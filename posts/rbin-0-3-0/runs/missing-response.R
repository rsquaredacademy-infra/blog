# rbin 0.3.0 release post: missing responses
# Run unchanged against CRAN 0.2.1 and CRAN 0.3.0:
#   Rscript missing-response.R "<library path>"
lib <- commandArgs(trailingOnly = TRUE)[1]
if (!is.na(lib) && nzchar(lib)) .libPaths(lib)
suppressWarnings(library(rbin))

cat("rbin", as.character(packageVersion("rbin")), "\n\n")

d <- mbank[, c("age", "y")]
d$y[c(3, 7, 11)] <- NA

rbin_equal_freq(d, y, age, bins = 4)
