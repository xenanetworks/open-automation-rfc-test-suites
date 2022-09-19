from typing import Dict, List
from rich.live import Live
from rich.table import Table
from rich.console import Console
import random, time

console = Console()


def generate_table(results: Dict) -> List[Table]:
    """Make a new table."""
    all_tables = []
    total_table = Table()
    total_table_row = []
    for k, v in results.items():
        if k not in {"Source Ports", "Destination Ports"}:
            total_table.add_column(k, no_wrap=True)
            total_table_row.append(str(v))
        else:
            for p in v:
                port_table = Table()
                port_table_row = []
                for t, m in p.items():
                    port_table.add_column(t, no_wrap=True)
                    port_table_row.append(str(m))
                port_table.add_row(*port_table_row)
                all_tables.append(port_table)

    total_table.add_row(*total_table_row)
    all_tables.append(total_table)

    return all_tables


def display(result):
    console.clear()
    tables = generate_table(result)
    for table in tables:
        with Live(console=console, screen=False, refresh_per_second=1) as live:        
            live.update(table)

