---
id: bulk-rnaseq-best-practice
name: Bulk RNA-seq 受控分析
description: 整数 count 矩阵才可进入 PyDESeq2；QC、设计公式、contrast、GSEA/ORA 背景与参数版本全部留痕。
version: 1.0.0
evidence_lanes: ["omics"]
scopes: ["disease_target_discovery", "bulk_rnaseq"]
---

# Bulk RNA-seq Best Practice

## 适用
公开 GEO/ArrayExpress bulk RNA-seq 数据的正式差异分析。

## 硬性规则
1. 只有非负整数 count 矩阵可以进入 PyDESeq2；TPM/FPKM/标准化表达量一律拒绝。
2. 连续表达矩阵或芯片 Series Matrix 仅在部署环境声明 limma 能力时使用固定 R 脚本；否则标记后端缺失。
3. 每组至少 3 个生物学重复；技术重复不能作为独立样本。
4. 分组置信度低于 0.8、病例对照混杂或数据格式不明时不得自动分析。

## 必留产物
- 样本分组与排除记录、设计公式、contrast、批次/配对变量；
- PCA、样本相关性、library size 和离群样本；
- 完整差异结果（FDR、效应方向）、GSEA 全排序结果、ORA 实际背景基因集；
- 原始文件校验和、参数、软件版本和随机种子。
