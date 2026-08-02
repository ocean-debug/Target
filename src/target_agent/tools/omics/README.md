# Omics Tools

主责：工作流 C；工作流 B 负责工具接入，工作流 F 负责可靠性与错误分析。

实现公开数据检索、Dataset Card、元数据标准化、QC、差异、通路、细胞状态和program分析。Notebook只能用于探索，最终能力必须封装成Agent可调用工具并返回`ToolResult`。

首批交付：一个主Demo数据集的QC和最小分析流程，以及一个数据质量不足案例。
