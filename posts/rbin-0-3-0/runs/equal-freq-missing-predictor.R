# rbin 0.3.0 release post: missing predictors in equal-frequency binning
# Run unchanged against CRAN 0.2.1 and CRAN 0.3.0:
#   Rscript equal-freq-missing-predictor.R "<library path>"
lib <- commandArgs(trailingOnly = TRUE)[1]
if (!is.na(lib) && nzchar(lib)) .libPaths(lib)
library(rbin)

cat("rbin", as.character(packageVersion("rbin")), "\n\n")

d <- mbank[, c("age", "y")]
missing_rows <- c(which(d$y == "0")[c(2, 5, 9)], which(d$y == "1")[4])
d$age[missing_rows] <- NA

rbin_equal_freq(d, y, age, bins = 4)
