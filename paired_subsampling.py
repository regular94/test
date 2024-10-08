'''
    Date: 2024-09-10
    Author: duaghk
    Optimizer: ChatGPT 4o
    Purpose: Paired subsampling bam.
'''

import pysam
import subprocess as sp
from time import time
from tqdm import tqdm
from pathlib import Path
from random import sample

# define class
class PairedSubsample:
    """
    A class for performing paired-end subsampling of a BAM file based on target sequencing depth.

    Attributes:
    ----------
    human_base : float
        The base number for human genome (hg38).
    
    Methods:
    -------
    calculate_target_read_number(read_len, adjust_val, target_depth, paired=True):
        Calculate the number of reads needed to achieve the target depth of sequencing.
    
    get_unique_query_names(bam_path):
        Get a unique list of query names from the BAM file.
    
    __call__(args):
        Perform the subsampling process and save the results to a new BAM file.
    """
    def __init__(self) -> None:
        """Initialize with human genome base size based on hg38."""
        self.human_base = 3.1e9  # base number based on hg38
        self.gatk_sif = Path("/storage/images/gatk-4.6.0.0.sif")
        self.fasta_path = Path("/storage/references_and_index/hg38/fasta/Homo_sapiens_assembly38.fasta")
        self.threads = 4

    def run_subprocess(func):
        """
        Decorator to run a shell command generated by the decorated function in a subprocess.

        The decorated function must return a string that represents the shell command to be executed.

        Args:
            func (function): The function that generates the shell command.

        Returns:
            function: The wrapper function that executes the shell command.
        """
        def wrapper(*args, **kwargs):
            cmd = func(*args, **kwargs)
            print(cmd)
            proc = sp.run(cmd, shell=True, universal_newlines=True, stdout=sp.PIPE, stderr=sp.PIPE)
            if proc.returncode:
                raise ChildProcessError(
                    f"Error occurred while running command: {cmd}\n"
                    f"stdout: {proc.stdout}\nstderr: {proc.stderr}"
                    )
            return proc.stdout  # 필요 시 stdout 반환
        return wrapper

    def calculate_target_read_number(
            self,
            read_len: int, 
            adjust_val: float, 
            target_depth: float, 
            paired: bool = True
            ) -> int:
        """
        Calculate the target number of reads based on the target depth of sequencing.

        Parameters:
        ----------
        read_len : int
            Length of the sequencing reads in base pairs.
        adjust_val : float
            Adjustment factor for oversampling.
        target_depth : float
            Desired depth of sequencing (e.g., 30 for 30X coverage).
        paired : bool, optional
            Whether the reads are paired-end, by default True.

        Returns:
        -------
        int
            The number of reads required to achieve the target depth.
        """
        # set read value.
        read_val = 2 if paired else 1
        read_count = round(self.human_base / read_len)  # primary read count for 1X
        read_count = round((read_count * adjust_val * target_depth)/read_val)
        return read_count

    @staticmethod
    def get_unique_query_names(bam_path):
        """
        Extract unique query names from a BAM file for subsampling.

        Parameters:
        ----------
        bam_path : str
            Path to the input BAM file.

        Returns:
        -------
        list
            A list of unique query names from the BAM file.
        """
        unique_query_list = []
        seen_query_names = set()  # Use a set for O(1) average lookup time
        
        with pysam.AlignmentFile(bam_path, "rb") as f:
            for read in tqdm(f):
                query_name = read.query_name
                if query_name not in seen_query_names:
                    seen_query_names.add(query_name)
                    unique_query_list.append(query_name)
        
        return unique_query_list
    
    @run_subprocess
    def mark_duplicates(self, subsampled_bam: Path, deduped_bam: Path, deduped_metrics: Path) -> str:
        """
            Mark duplicates in the subsampled BAM file using GATK MarkDuplicatesSpark.

            This method runs GATK MarkDuplicatesSpark with options to remove sequencing duplicates
            and use Spark for parallel processing.

            Parameters:
            ----------
            subsampled_bam : Path
                Path to the input subsampled BAM file.
            deduped_bam : Path
                Path to the output BAM file where duplicates are marked and removed.
            deduped_metrics : Path
                Path to the output metrics file that will store duplication metrics.

            Returns:
            -------
            str
                The shell command to be executed for marking duplicates.
        """
        cmd = (
            f"singularity exec "
            f"-B /storage,/data "
            f"{self.gatk_sif} "
            f"gatk MarkDuplicatesSpark "
            f"--remove-sequencing-duplicates "
            f"-I {subsampled_bam} "
            f"-O {deduped_bam} "
            f"-M {deduped_metrics} "
            "-- "
            f"--spark-master local[{self.threads}] "
            f"--conf 'spark.executor.memory=8G' "
            f"--conf 'spark.local.dir=/data/tmp'"
        )
        return cmd

    @run_subprocess
    def collect_wgs_metric(self, deduped_bam: Path, wgs_metric: Path) -> str:
        """
            Collect WGS metrics from the deduplicated BAM file using GATK CollectWgsMetrics.

            This method runs GATK CollectWgsMetrics with specific Java options for memory allocation
            and parallel garbage collection.

            Parameters:
            ----------
            deduped_bam : Path
                Path to the input deduplicated BAM file.
            wgs_metric : Path
                Path to the output WGS metrics file.

            Returns:
            -------
            str
                The shell command to be executed for collecting WGS metrics.
        """
        # Construct the shell command for CollectWgsMetrics
        cmd = (
            f"singularity exec "
            f"-B /storage,/data "
            f"{self.gatk_sif} "
            f"gatk "
            f"--java-options "
            f"\"-Xmx16G -XX:ConcGCThreads={self.threads} -Djava.io.tmpdir=/data/tmp\" "
            f"CollectWgsMetrics "
            f"-R {self.fasta_path} "
            f"-I {deduped_bam} "
            f"-O {wgs_metric}"
        )
        return cmd

    def __call__(self, args) -> Path:
        """
        Execute the paired-end subsampling process based on the target read count.

        Parameters:
        ----------
        args : argparse.Namespace
            Arguments containing BAM file paths, target depth, and other configurations.

        Returns:
        -------
        Path
            Path to the newly created subsampled BAM file.
        """
        # Logging input
        start = time()
        # create output directory.
        sample_id = args.bam_path.name.split(".")[0]
        output_dir = args.output_dir.joinpath(sample_id)
        output_dir.mkdir(parents=True, exist_ok=True)
        print(f"Target depth: {args.target_depth}")
        target_read_count = self.calculate_target_read_number(args.read_len, args.adjust_val, args.target_depth, args.paired)
        print(f"Target-need read count: {target_read_count}")
        # Get unique query name list.
        unique_query_list = self.get_unique_query_names(args.bam_path)

        if target_read_count > len(unique_query_list):
            raise ValueError(f"Insufficient unique query names ({len(unique_query_list)}) for target read count ({target_read_count}). Exiting.")
        # sampling.
        sampled = set(sample(unique_query_list, target_read_count))
        # save.
        subsampled_bam_path = output_dir.joinpath(f"{sample_id}.paired-subsampled.bam")
        with pysam.AlignmentFile(args.bam_path) as fread:
            with pysam.AlignmentFile(subsampled_bam_path, 'wb', header=fread.header) as fwrite:
                for read in tqdm(fread):
                    if read.query_name in sampled:
                        if read.flag & 0x400:
                            read.flag &= ~0x400  # Remove the duplicate flag
                        fwrite.write(read)
        
        # MarkDuplications.
        deduped_bam_path = output_dir.joinpath(f"{sample_id}.paired-subsampled.deduped.bam")
        deduped_bam_metric_path = output_dir.joinpath(f"{sample_id}.paired-subsampled.deduped.bam.metrics.txt")
        self.mark_duplicates(subsampled_bam_path, deduped_bam_path, deduped_bam_metric_path)

        # CollectWGSmetrics.
        wgs_metric_path = output_dir.joinpath(f"{sample_id}.paired-subsampled.deduped.bam.wgs-metrics.txt")
        self.collect_wgs_metric(deduped_bam_path, wgs_metric_path)        
        print(f"Elapsed time: {time()-start:.3f}s")
        pass


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="Paired-end subsampling of a BAM file based on target read depth.")
    
    # Required arguments
    parser.add_argument("--bam_path", type=Path, help="Input BAM file path")
    parser.add_argument("--output_dir", type=Path, help="Output directory")

    # Optional arguments with default values
    parser.add_argument("--read_len", type=int, default=150, help="Read length in base pairs (default: 150)")
    parser.add_argument("--adjust_val", type=float, default=1.2, help="Adjustment value for oversampling (default: 1.2)")
    parser.add_argument("--target_depth", type=float, required=True, help="Target depth of sequencing coverage (e.g., 30 for 30X coverage)")
    parser.add_argument("--paired", action="store_true", default=False, help="Whether the BAM file contains paired-end reads (default: False)")    
    args = parser.parse_args()

    # Instantiate and run the subsampling
    subsampler = PairedSubsample()
    subsampler(args)


# # Run script?
# python3.9 ~/build/modules/cbNIPT/call_cnv/other_tool_script/subsampling/paired_subsample.py \
# --bam_path /data/cbNIPT/hg38/TBD240401_20319_20240402/cbNIPT04-4/bam/cbNIPT04-4.recaled.bam \
# --output_path /data/cbNIPT/test/subsample/test2/test.bam \
# --read_len 135 \
# --adjust_val 1.2 \
# --target_depth 0.5 \
# --paired


