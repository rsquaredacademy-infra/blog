# rbin 0.3.0 release post: tied values in equal-frequency binning
# Run unchanged against CRAN 0.2.1 and CRAN 0.3.0:
#   Rscript equal-freq-ties.R "<library path>"
lib <- commandArgs(trailingOnly = TRUE)[1]
if (!is.na(lib) && nzchar(lib)) .libPaths(lib)
suppressWarnings(library(rbin))

cat("rbin", as.character(packageVersion("rbin")), "\n\n")

d <- mbank[, c("previous", "y")]

rbin_equal_freq(d, y, previous, bins = 5)
