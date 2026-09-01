"""Universe-wide composite indicator matrix calculation engine."""

from __future__ import annotations

import logging
from datetime import datetime
from typing import Any

import pyarrow as pa
import pyarrow.compute as pc

from app.indicators.graph import IndicatorDependencyGraph
from app.warehouse.reader import WarehouseReader
from app.warehouse.schema import BarRecord, bars_to_arrow_table

logger = logging.getLogger(__name__)


class UniverseIndicatorMatrixEngine:
    """Computes technical indicator matrices across multi-instrument universes."""

    def __init__(self, reader: WarehouseReader | None = None) -> None:
        self.reader = reader

    def compute_matrix_from_table(
        self,
        table: pa.Table,
        graph: IndicatorDependencyGraph,
    ) -> pa.Table:
        """Compute indicator matrix from a multi-instrument PyArrow Table."""
        if table.num_rows == 0:
            return table

        plan = graph.compile_plan()
        symbol_col = table["symbol"].to_pylist()
        symbols = sorted(set(symbol_col))

        output_chunks: list[pa.Table] = []

        for sym in symbols:
            # Filter rows for this symbol
            mask = pc.equal(table["symbol"], sym)
            sym_table = table.filter(mask)
            # Sort by timestamp
            sort_indices = pc.sort_indices(sym_table["timestamp"])
            sym_table = sym_table.take(sort_indices)

            sym_dict: dict[str, Any] = {
                col: sym_table[col].to_pylist() for col in sym_table.column_names
            }
            node_results = plan.execute(sym_dict)

            # Append calculated columns
            new_columns = list(sym_table.columns)
            new_names = list(sym_table.column_names)

            for node_name in plan.execution_order:
                series = node_results[node_name]
                arr = pa.array(series)
                new_columns.append(arr)
                new_names.append(node_name)

            chunk = pa.Table.from_arrays(new_columns, names=new_names)
            output_chunks.append(chunk)

        if not output_chunks:
            return table

        full_table = pa.concat_tables(output_chunks)
        # Sort full table by timestamp then symbol
        sort_indices = pc.sort_indices(
            full_table,
            sort_keys=[("timestamp", "ascending"), ("symbol", "ascending")],
        )
        return full_table.take(sort_indices)

    def compute_matrix_from_bars(
        self,
        bars: list[BarRecord],
        graph: IndicatorDependencyGraph,
    ) -> pa.Table:
        """Compute indicator matrix from a list of BarRecords."""
        if not bars:
            return pa.Table.from_arrays([], names=[])
        table = bars_to_arrow_table(bars)
        return self.compute_matrix_from_table(table, graph)

    def compute_matrix(
        self,
        symbols: list[str],
        graph: IndicatorDependencyGraph,
        start_time: datetime | str | None = None,
        end_time: datetime | str | None = None,
        segment: str | None = None,
        reader: WarehouseReader | None = None,
    ) -> pa.Table:
        """Query warehouse and compute universe-wide indicator matrix."""
        active_reader = reader or self.reader or WarehouseReader()
        table = active_reader.query_bars(
            symbols=symbols,
            segment=segment,
            start_time=start_time,
            end_time=end_time,
        )
        return self.compute_matrix_from_table(table, graph)
