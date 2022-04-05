import json
import re

import pandas as pd
from matplotlib import pyplot as plt


class CategoryAssigner:
    """Assigns categories and names to transactions based on counterparty name.

    Assigns categories and names by checking transaction counterparty names with
        regexes from a regex map. The assigned category and name is the one corresponding
        to the first regex which matches the counterparty name.

    """

    def __init__(self, regex_map):
        """Initialize the assigner.

        Args:
            regex_map(list[tuple[str, str, str]]: Mapping of regexes to names and categories
                as list of tuples (regex, name, category).

        """
        self._regex_map = regex_map

    @classmethod
    def from_json(cls, filepath):
        """Load the regex map from JSON file and get initialized assigner.

        The file has to contain one list of dicts, where each dict contains keys "name",
            "regex" and "category" and the values are strings.

        Args:
            filepath(str): Path to JSON file containing the regex map.

        Returns:
            (CategoryAssigner): Assigner initialized with the loaded regex map.

        """
        regex_map = []
        with open(filepath, "r") as f:
            for item in json.load(f):
                name = item["name"]
                regex = item["regex"]
                category = item["category"]
                regex_map.append((regex, name, category))
        return cls(regex_map)

    def get_category(self, counterparty):
        """Get item category for the given counterparty.

        Args:
            counterparty (str): Name of counterparty of the transaction.

        Returns:
            str: Category of the transaction.

        """
        for regex, name, category in self._regex_map:
            if re.match(regex, counterparty):
                return category
        return "unknown category"

    def get_name(self, counterparty):
        """Get item name for the given counterparty.

        Args:
            counterparty (str): Name of counterparty of the transaction.

        Returns:
            str: Name of the transaction.

        """
        for regex, name, category in self._regex_map:
            if re.match(regex, counterparty):
                return name
        return "unknown name"


class StatementData:
    """Loads, parses and holds the data from the bank statement."""

    def __init__(self, statement_filepath, categories_filepath):
        """Load and parse the data.

        Args:
            statement_filepath: Path to the statement CSV.
            categories_filepath: Path to JSON defining categories.

        """
        self._category_assigner = CategoryAssigner.from_json(categories_filepath)
        self._df = self._parse(statement_filepath)

    def _parse(self, statement_filepath):
        """Load and parse the data.

        Args:
            statement_filepath: Path to the statement CSV.

        Returns:
            pandas.DataFrame: The loaded and parsed data.

        """
        # load from csv
        df = pd.read_csv(
            statement_filepath, encoding="windows-1250", delimiter=";", skiprows=17
        )

        # get only certain columns
        df = df[df.columns[[0, 4, 15, 18]]]
        df.columns = ["due date", "amount", "counterparty", "date"]

        # create date column
        df["date"] = df["date"].apply(lambda x: x[:10])
        df["date"] = df.apply(
            lambda row: row["due date"] if row["date"] == " " * 10 else row["date"],
            axis=1,
        )

        # convert date strings to datetime
        df["date"] = pd.to_datetime(df["date"], format="%d.%m.%Y")
        df["due date"] = pd.to_datetime(df["due date"], format="%d.%m.%Y")

        # convert amount to numeric
        df["amount"] = pd.to_numeric(df["amount"].str.replace(",", "."))

        # assign categories
        df["category"] = df.apply(
            lambda row: self._category_assigner.get_category(row["counterparty"]),
            axis=1,
        )
        df["name"] = df.apply(
            lambda row: self._category_assigner.get_name(row["counterparty"]), axis=1
        )

        return df

    def print_unknown_categories(self):
        """Print unknown categories, so they can be manually added to the JSON."""
        print(
            self._df[self._df["category"] == "unknown category"][
                ["date", "amount", "counterparty"]
            ]
        )

    def show_expense_pie_chart(self):
        """Show pie chart of expenses."""
        df_spent = self._df[["amount", "category"]][self._df["amount"] < 0]
        df_spent["amount"] *= -1
        df_spent = df_spent.groupby(["category"]).sum()
        spent_total = df_spent["amount"].sum()
        df_spent.plot.pie(
            y="amount", autopct=lambda x: "{:.0f} Kč".format(x * spent_total / 100)
        )
        plt.show()


if __name__ == "__main__":
    data = StatementData("example_statement.csv", "categories.json")
    data.print_unknown_categories()
    data.show_expense_pie_chart()
