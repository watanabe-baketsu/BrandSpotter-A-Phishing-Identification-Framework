import os

import matplotlib.pyplot as plt
import pandas as pd

from datasets import load_from_disk
from src.config import SETFIT_RESULT_DIR


class ResultAnalyzer:
    def __init__(self, result_path: str, mode="csv"):
        if mode == "csv":
            self.df = pd.read_csv(result_path)
        else:
            results = load_from_disk(result_path)
            self.df = results.to_pandas()

    def get_accuracy(self) -> float:
        return self.df["correct"].sum() / self.df.shape[0]

    @staticmethod
    def calc_metrics_by_brand(t_df) -> pd.DataFrame:
        # calculate recall by brand
        df_recall = t_df.groupby("answer").agg({"correct": ["sum", "count"]})
        df_recall.columns = ["correct_sum", "count"]
        df_recall["recall"] = df_recall["correct_sum"] / df_recall["count"]
        df_recall = df_recall.drop(["correct_sum"], axis=1)
        # calculate precision by brand
        df_precision = t_df.groupby("identified").agg(
            {"correct": "sum", "identified": "count"}
        )
        df_precision.columns = ["correct_sum", "identified_count"]
        df_precision["precision"] = (
            df_precision["correct_sum"] / df_precision["identified_count"]
        )
        df_precision = df_precision.drop(["correct_sum", "identified_count"], axis=1)

        df = pd.merge(
            df_recall[["recall", "count"]],
            df_precision[["precision"]],
            left_index=True,
            right_index=True,
            how="outer",
        )
        df = df.fillna(0)
        df["f1"] = (
            2 * (df["precision"] * df["recall"]) / (df["precision"] + df["recall"])
        )
        df["f1"] = df["f1"].fillna(0)

        df = df.sort_values(by="count", ascending=False)
        df = df[["count", "recall", "precision", "f1"]]
        return df

    @staticmethod
    def get_summary_plot(df, path: str):
        fig, axs = plt.subplots(3, 1, figsize=(10, 15), sharex=True)

        # Display count bar graph and recall line graph overlaid
        ax1 = axs[0]
        ax1.bar(df.index, df["count"], color="tab:blue", alpha=0.6, label="Count")
        ax1.set_ylabel("Count")
        ax2 = ax1.twinx()
        ax2.plot(df.index, df["recall"], "tab:orange", label="Recall")
        ax2.set_ylabel("Recall")
        ax1.legend(loc="upper left")
        ax2.legend(loc="upper right")

        # Display count bar graph and precision line graph overlaid
        ax1 = axs[1]
        ax1.bar(df.index, df["count"], color="tab:blue", alpha=0.6, label="Count")
        ax1.set_ylabel("Count")
        ax2 = ax1.twinx()
        ax2.plot(df.index, df["precision"], "tab:green", label="Precision")
        ax2.set_ylabel("Precision")
        ax1.legend(loc="upper left")
        ax2.legend(loc="upper right")

        # Display count bar graph and f1 line graph overlaid
        ax1 = axs[2]
        ax1.bar(df.index, df["count"], color="tab:blue", alpha=0.6, label="Count")
        ax1.set_ylabel("Count")
        ax2 = ax1.twinx()
        ax2.plot(df.index, df["f1"], "tab:red", label="F1 Score")
        ax2.set_ylabel("F1 Score")
        ax1.legend(loc="upper left")
        ax2.legend(loc="upper right")

        # Hide X-axis labels
        for ax in axs:
            ax.tick_params(axis="x", labelsize=0)

        fig.tight_layout()
        plt.savefig(f"{path}/summary_plot.pdf", bbox_inches="tight")
        plt.show()

    @staticmethod
    def get_recall_plot(df: pd.DataFrame, path: str):
        fig, ax1 = plt.subplots()

        # Display count bar graph and recall line graph overlaid
        ax1.bar(df.index, df["count"], color="tab:blue", alpha=0.6, label="Count")
        ax1.set_ylabel("Count [samples]", fontsize=14)
        ax1.tick_params(axis="x", labelsize=0)  # Hide X-axis labels
        ax2 = ax1.twinx()
        ax2.plot(df.index, df["recall"], "tab:orange", label="Recall")
        ax2.set_ylabel("Recall", fontsize=14)
        ax1.legend(loc="lower left", fontsize=14)
        ax2.legend(loc="lower right", fontsize=14)
        plt.savefig(f"{path}/recall_plot.pdf", bbox_inches="tight")
        plt.show()

    @staticmethod
    def get_precision_plot(df: pd.DataFrame, path: str):
        fig, ax1 = plt.subplots()

        # Display count bar graph and precision line graph overlaid
        ax1.bar(df.index, df["count"], color="tab:blue", alpha=0.6, label="Count")
        ax1.set_ylabel("Count [samples]", fontsize=14)
        ax1.tick_params(axis="x", labelsize=0)
        ax2 = ax1.twinx()
        ax2.plot(df.index, df["precision"], "tab:green", label="Precision")
        ax2.set_ylabel("Precision", fontsize=14)
        ax1.legend(loc="lower left", fontsize=14)
        ax2.legend(loc="lower right", fontsize=14)
        plt.savefig(f"{path}/precision_plot.pdf", bbox_inches="tight")
        plt.show()

    @staticmethod
    def get_low_metrics_brand(
        metrics: pd.DataFrame, count_threshold: int, metrics_threshold
    ) -> pd.DataFrame:
        metrics = metrics[metrics["count"] >= count_threshold]
        f1_metrics = metrics[metrics["f1"] <= metrics_threshold]
        precision_metrics = metrics[metrics["precision"] <= metrics_threshold]
        recall_metrics = metrics[metrics["recall"] <= metrics_threshold]
        metrics = pd.concat(
            [f1_metrics, precision_metrics, recall_metrics], axis=0
        ).drop_duplicates()
        metrics = metrics.sort_values(by="count", ascending=False)
        return metrics

    def get_specified_brand_incorrect_samples(self, brand: str) -> pd.DataFrame:
        df = self.df[self.df["answer"] == brand]
        df = df[df["correct"] == 0]
        return df

    def get_specified_brand_correct_samples(self, brand: str) -> pd.DataFrame:
        df = self.df[self.df["answer"] == brand]
        df = df[df["correct"] == 1]
        return df

    def get_specified_brands_metrics(self, targets: list) -> pd.DataFrame:
        df = self.df[self.df["answer"].isin(targets)]
        df = self.calc_metrics_by_brand(df)
        return df


def print_save_specified_samples(df: pd.DataFrame, file_name: str):
    print(f"inference : {df['inference'].tolist()[0]}")
    print(f"identified : {df['identified'].tolist()[0]}")
    with open(os.path.join(SETFIT_RESULT_DIR, file_name), "w", encoding="utf-8") as f:
        f.write(df["html"].tolist()[0])
    print("")


def analyze_only_eval_label_samples(analyzer: ResultAnalyzer, only_test_labels: list):
    only_df = analyzer.get_specified_brands_metrics(only_test_labels)
    print(only_df)

    # print("### unseen label correct sammple ###")
    # correct_df = analyzer.get_specified_brand_correct_samples("Monmouth Telecom")
    # print_save_specified_samples(correct_df, "only_eval_label_correct_sample.txt")

    # print("### unseen label incorrect sammple ###")
    # incorrect_df = analyzer.get_specified_brand_incorrect_samples(
    #     "Credit Agricole S.A."
    # )
    # print_save_specified_samples(incorrect_df, "only_eval_label_incorrect_sample.txt")


def analyze_low_metric_samples(analyzer: ResultAnalyzer):
    low_metrics_df = analyzer.get_low_metrics_brand(analyzer.df, 10, 0.8)
    print(low_metrics_df)

    print("### low metric correct sammple ###")
    correct_df = analyzer.get_specified_brand_correct_samples(
        "Alaska USA Federal Credit Union"
    )
    print_save_specified_samples(correct_df, "low_metric_correct_sample.txt")

    print("### low metric incorrect sammple ###")
    incorrect_df = analyzer.get_specified_brand_incorrect_samples(
        "Alaska USA Federal Credit Union"
    )
    print_save_specified_samples(incorrect_df, "low_metric_incorrect_sample.txt")


if __name__ == "__main__":
    base_path = SETFIT_RESULT_DIR
    path = os.path.join(base_path, "poc_results.csv")
    analyzer = ResultAnalyzer(path)
    print(analyzer.df.columns)

    print(f"accuracy : {analyzer.get_accuracy()}")
    metrics_df = analyzer.calc_metrics_by_brand(analyzer.df)
    print(metrics_df)

    analyzer.get_recall_plot(metrics_df, base_path)
    analyzer.get_precision_plot(metrics_df, base_path)

    # only_test_labels = [
    #     'Movistar'
    # ]
    # only_test_labels = analyzer.df["answer"].unique().tolist()
    # analyze_only_eval_label_samples(analyzer, only_test_labels)

    # metrics_df.to_csv(f"{base_path}/sm_only_eval_metrics.csv", index=False)
    analyzer.get_summary_plot(metrics_df, base_path)
    #
    # analyze_low_metric_samples(analyzer)
