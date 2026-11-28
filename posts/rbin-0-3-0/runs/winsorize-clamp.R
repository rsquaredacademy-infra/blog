# rbin 0.3.0 release post: winsorized fit and scoring with clamp endpoints
# Run unchanged against CRAN 0.2.1 and CRAN 0.3.0:
#   Rscript winsorize-clamp.R "<library path>"
lib <- commandArgs(trailingOnly = TRUE)[1]
if (!is.na(lib) && nzchar(lib)) .libPaths(lib)
suppressWarnings(library(rbin))

cat("rbin", as.character(packageVersion("rbin")), "\n\n")

d <- mbank[, c("duration", "y")]

bins <- rbin_winsorize(
  d, y, duration,
  bins = 4,
  min_val = 100, max_val = 600
)
print(bins)

cat("\nScoring values outside the training range:\n")
new_data <- data.frame(duration = c(50, 100, 350, 600, 900))
tryCatch(
  print(rbin_create(new_data, duration, bins)),
  error = function(e) cat("Error:", conditionMessage(e), "\n")
)
