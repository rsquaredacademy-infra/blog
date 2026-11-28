lib <- commandArgs(TRUE)[1]
.libPaths(c(lib, .libPaths()))
suppressPackageStartupMessages(library(descriptr))
cat("version:", as.character(packageVersion("descriptr")), "\n")

set.seed(2026)
orders <- data.frame(
  order_id = 1:600,
  region = factor(sample(c("North", "South", "East", "West"), 600, TRUE, prob = c(.3, .25, .25, .2))),
  channel = sample(c("Web", "Store", "Partner"), 600, TRUE),
  order_value = round(rlnorm(600, 6.6, 0.55)),
  delivery_days = rpois(600, 4) + 1,
  discount_pct = sample(0:30, 600, TRUE)
)
orders$order_value[sample(600, 40)] <- NA
orders$region[c(12, 140, 377)] <- NA

cat("=== freq discount ===\n")
print(tryCatch(ds_freq_table(orders, discount_pct, bins = 5), error = function(e) paste("ERROR:", conditionMessage(e))))
cat("=== variation ===\n")
print(tryCatch(ds_measures_variation(orders), error = function(e) paste("ERROR:", conditionMessage(e))))
cat("=== group summary ===\n")
print(tryCatch(ds_group_summary(orders, region, order_value), error = function(e) paste("ERROR:", conditionMessage(e))))
cat("=== cross table ===\n")
print(tryCatch(ds_cross_table(orders, region, channel), error = function(e) paste("ERROR:", conditionMessage(e))))
cat("=== extreme obs ===\n")
print(tryCatch(ds_extreme_obs(orders, order_value), error = function(e) paste("ERROR:", conditionMessage(e))))
cat("=== tidy stats ===\n")
print(tryCatch(ds_tidy_stats(orders), error = function(e) paste("ERROR:", conditionMessage(e))))
cat("=== decimals 1 ===\n")
print(tryCatch(ds_measures_variation(orders, decimals = 1), error = function(e) paste("ERROR:", conditionMessage(e))))
cat("=== gmean large ===\n")
print(tryCatch(ds_gmean(c(1e300, 2e300, 3e300)), error = function(e) paste("ERROR:", conditionMessage(e))))
