args <- commandArgs(trailingOnly = TRUE)
if (length(args) != 3) {
  stop("usage: limma_expression.R expression.csv metadata.csv result.csv")
}
if (!requireNamespace("limma", quietly = TRUE)) {
  stop("the limma R package is not installed")
}

expression <- read.csv(args[[1]], row.names = 1, check.names = FALSE)
metadata <- read.csv(args[[2]], row.names = 1, check.names = FALSE)
if (!identical(colnames(expression), rownames(metadata))) {
  stop("expression columns and metadata rows are not aligned")
}
metadata$condition <- factor(metadata$condition, levels = c("control", "case"))
design <- model.matrix(~ condition, data = metadata)
if (qr(design)$rank < ncol(design)) {
  stop("design matrix is not full rank")
}
fit <- limma::lmFit(expression, design)
fit <- limma::eBayes(fit)
result <- limma::topTable(fit, coef = "conditioncase", number = Inf, sort.by = "P")
result$feature_id <- rownames(result)
rownames(result) <- NULL
write.csv(result, args[[3]], row.names = FALSE)
