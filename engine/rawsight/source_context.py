from __future__ import annotations

import os
from pathlib import Path
from typing import Any

import duckdb

from rawsight.datasets import open_dataset


def _normalized_path(file_path: str) -> str:
    """
    Normalize a source path for lifecycle-safety comparisons.

    normcase is significant on Windows and harmless on case-sensitive
    platforms.
    """

    return os.path.normcase(
        os.path.abspath(file_path)
    )


def _quote_identifier(name: str) -> str:
    return '"' + name.replace('"', '""') + '"'


class SourceExecutionContext:
    """
    Own one DuckDB source session for one RAWSIGHT execution path.

    The context owns:
      - DuckDB connection
      - opened source relation
      - shared source view
      - column names/types
      - deterministic close lifecycle

    Analysis modules may share this context but must not close it unless
    they created it themselves.
    """

    def __init__(
        self,
        file_path: str,
        view_name: str = "rawsight_source",
    ) -> None:
        self.file_path = str(
            Path(file_path)
        )
        self.view_name = view_name

        self.connection: (
            duckdb.DuckDBPyConnection | None
        ) = None
        self.relation: Any | None = None

        self.column_names: list[str] = []
        self.column_types: list[str] = []

        self._normalized_file_path = (
            _normalized_path(
                self.file_path
            )
        )

    @property
    def is_open(self) -> bool:
        return self.connection is not None

    def assert_source(
        self,
        file_path: str,
    ) -> None:
        if (
            _normalized_path(file_path)
            != self._normalized_file_path
        ):
            raise ValueError(
                "SourceExecutionContext belongs to "
                "a different source file"
            )

    def open(self) -> "SourceExecutionContext":
        if self.is_open:
            return self

        connection = duckdb.connect()

        try:
            relation = open_dataset(
                connection,
                self.file_path,
            )

            column_names = list(
                relation.columns
            )
            column_types = [
                str(data_type)
                for data_type in relation.types
            ]

            relation.create_view(
                self.view_name,
                replace=True,
            )

        except Exception:
            connection.close()
            raise

        self.connection = connection
        self.relation = relation
        self.column_names = column_names
        self.column_types = column_types

        return self

    def require_connection(
        self,
    ) -> duckdb.DuckDBPyConnection:
        if self.connection is None:
            raise RuntimeError(
                "SourceExecutionContext is not open"
            )

        return self.connection

    def select_all_cursor(self):
        connection = (
            self.require_connection()
        )

        view = _quote_identifier(
            self.view_name
        )

        return connection.execute(
            f"SELECT * FROM {view}"
        )

    def close(self) -> None:
        connection = self.connection

        self.connection = None
        self.relation = None
        self.column_names = []
        self.column_types = []

        if connection is not None:
            connection.close()

    def __enter__(
        self,
    ) -> "SourceExecutionContext":
        return self.open()

    def __exit__(
        self,
        exc_type,
        exc_value,
        traceback,
    ) -> None:
        self.close()
