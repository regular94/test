# Draw Oncoprint for GCGIL
if (!requireNamespace("openxlsx", quietly=TRUE))
  install.packages("openxlsx")
if (!requireNamespace("BiocManager", quietly=TRUE))
  install.packages("BiocManager")
BiocManager::install("ComplexHeatmap")

library(openxlsx)
library(ComplexHeatmap)

if (getwd() != "/home/rstudio/test")
  setwd("test")
# Read data
data = read.csv("gcu_kys_mutation_all.csv", row.names = 1)
data$CD_21_06802_DP_CS = ""
# Read info data
info_data = read.xlsx("gcu_kys_sample_info.xlsx")
# replace info_data. columns
colnames(info_data)
rownames(info_data) = info_data$Geninus.ID
info_data = info_data[colnames(data), ]

# Rename rownames.
# check if row name equal.
rownames(info_data) == colnames(data)
# Rename data's col name to masked ID
colnames(data) = info_data$Sbj_Code
# Rename info_data's row name to masked ID
rownames(info_data) = info_data$Sbj_Code

# set value by factor and set level
info_data$response = factor(info_data$response, levels = c("CR", "PR", "SD", "PD", "NE"))
info_data$MSI=factor(info_data$MSI,levels=c("Low","High"))
info_data$`PD-L1.SP263` = factor(info_data$`PD-L1.SP263`, levels = c("0", "<1", "1 -<5", "1 - 9", "5 -<10", "20 -<30", "60 -<70"))

# Set color
col = c(SNV = "green4", AMP = "red", DEL="blue")
# draw plot
oncop = oncoPrint(data,
                  alter_fun = list(
                    background = function(x, y, w, h) {
                      grid.rect(x, y, w*0.9, h*0.9, 
                                gp = gpar(fill = "#CCCCCC", col = NA))
                    },
                    SNV = function(x, y, w, h) grid.rect(x, y, w*0.9, h*0.9, 
                                                         gp = gpar(fill = col["SNV"], col=col["SNV"])),
                    AMP = function(x, y, w, h) grid.rect(x, y, w*0.9, h*0.4, gp = gpar(fill = col["AMP"], col = NA)),
                    DEL = function(x, y, w, h) grid.rect(x, y, w*0.9, h*0.4, gp = gpar(fill = col["DEL"], col = NA))),
                  col = col,
                  show_column_names = T,
                  top_annotation = HeatmapAnnotation(
                    cbar = anno_oncoprint_barplot(),
                    Response=info_data$response,
                    `PD-L1(SP263)` = info_data$`PD-L1.SP263`,
                    MSI=info_data$MSI, 
                    TMB=info_data$TMB),
                  remove_empty_columns = FALSE,
                  column_split = info_data$response,
                  column_title = "Oncoprint for EAGLES study\n(count >2)",
                  column_title_gp = gpar(fontface="bold"),
                  gap=1
)
draw(oncop, merge_legend=TRUE, heatmap_legend_side = "right", annotation_legend_side = "right")
