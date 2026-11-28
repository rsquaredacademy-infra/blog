# rbin 0.3.0 release post: rbin_create() on the 0.2.1 summary for tied values
# Run against CRAN 0.2.1 and CRAN 0.3.0:
#   Rscript equal-freq-ties-create.R "<library path>"
lib <- commandArgs(trailingOnly = TRUE)[1]
if (!is.na(lib) && nzchar(lib)) .libPaths(lib)
suppressWarnings(library(rbin))

cat("rbin", as.character(packageVersion("rbin")), "\n\n")

d <- mbank[, c("previous", "y")]
b <- rbin_equal_freq(d, y, previous, bins = 5)
print(b)

cat("\nrbin_create() on the same summary:\n")
tryCatch(
  print(rbin_create(d[1:10, ], previous, b)),
  error = function(e) cat("Error:", conditionMessage(e), "\n")
)
