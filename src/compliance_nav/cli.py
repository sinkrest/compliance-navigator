"""CLI for the Compliance Navigator."""

import json
import sys

import click
from rich.console import Console
from rich.panel import Panel
from rich.table import Table

from .models import ComplianceResult, Product
from .navigator import check_compliance, load_product_from_yaml

console = Console()


def _render_rich(result: ComplianceResult) -> None:
    """Render compliance result with rich formatting."""
    product = result.product

    # Header
    console.print()
    console.print(
        Panel(
            f"[bold]{product.name}[/bold]\n"
            f"Types: {', '.join(product.types)}\n"
            f"Markets: {', '.join(product.markets)}\n"
            f"{product.description}" if product.description else "",
            title="Compliance Check",
            border_style="blue",
        )
    )

    # Warnings
    if result.warnings:
        console.print()
        for w in result.warnings:
            console.print(f"  [yellow]⚠ {w}[/yellow]")

    # Applicable Directives
    if result.applicable_directives:
        console.print()
        table = Table(title="Applicable EU Directives", show_lines=True)
        table.add_column("Directive", style="bold cyan", width=12)
        table.add_column("Name", width=30)
        table.add_column("Scope", width=50)

        for d in result.applicable_directives:
            table.add_row(
                f"{d.short_name}\n{d.id}",
                d.full_name,
                d.scope[:120] + "..." if len(d.scope) > 120 else d.scope,
            )
        console.print(table)

    # Applicable Standards
    if result.applicable_standards:
        console.print()
        table = Table(title="Applicable Standards")
        table.add_column("Standard", style="bold")
        table.add_column("Description")

        for s in result.applicable_standards:
            table.add_row(s.id, s.scope)
        console.print(table)

    # Compliance Checklist
    if result.checklist:
        console.print()
        table = Table(title="Compliance Checklist", show_lines=True)
        table.add_column("", width=3)
        table.add_column("Action", width=50)
        table.add_column("Category", width=14)
        table.add_column("Est. Cost", width=16)

        for item in result.checklist:
            priority_icon = {
                "required": "[red]●[/red]",
                "recommended": "[yellow]○[/yellow]",
                "optional": "[dim]○[/dim]",
            }.get(item.priority, "○")

            table.add_row(
                priority_icon,
                f"[bold]{item.directive_id}[/bold]: {item.action}",
                item.category,
                item.estimated_cost or "–",
            )
        console.print(table)
        console.print("  [red]●[/red] Required  [yellow]○[/yellow] Recommended  [dim]○[/dim] Optional")

    # Risk Notes
    if result.risk_notes:
        console.print()
        console.print(Panel(
            "\n".join(f"• {note}" for note in result.risk_notes),
            title="Risk Notes (from recall data)",
            border_style="red",
        ))

    # Related Recalls
    if result.related_recalls:
        console.print()
        table = Table(title=f"Related Recalls ({len(result.related_recalls)} most recent)")
        table.add_column("Date", width=12)
        table.add_column("Product", width=30)
        table.add_column("Hazard", width=40)
        table.add_column("Units", width=15)

        for r in result.related_recalls[:10]:  # Show top 10
            table.add_row(
                r.date[:10] if r.date else "–",
                r.product_name[:28] + "..." if len(r.product_name) > 30 else r.product_name,
                r.hazard[:38] + "..." if len(r.hazard) > 40 else r.hazard,
                r.units[:13] + "..." if len(r.units) > 15 else r.units,
            )
        console.print(table)

    console.print()


def _render_json(result: ComplianceResult) -> None:
    """Render compliance result as JSON."""
    output = {
        "product": {
            "name": result.product.name,
            "types": result.product.types,
            "markets": result.product.markets,
        },
        "directives": [
            {
                "id": d.id,
                "short_name": d.short_name,
                "full_name": d.full_name,
                "url": d.url,
            }
            for d in result.applicable_directives
        ],
        "standards": [
            {"id": s.id, "name": s.name}
            for s in result.applicable_standards
        ],
        "checklist": [
            {
                "directive": item.directive_id,
                "action": item.action,
                "category": item.category,
                "priority": item.priority,
                "estimated_cost": item.estimated_cost,
            }
            for item in result.checklist
        ],
        "risk_notes": result.risk_notes,
        "warnings": result.warnings,
        "related_recalls_count": len(result.related_recalls),
    }
    print(json.dumps(output, indent=2))


def _render_markdown(result: ComplianceResult) -> None:
    """Render compliance result as Markdown."""
    p = result.product
    lines = [
        f"# Compliance Check: {p.name}",
        "",
        f"**Types:** {', '.join(p.types)}",
        f"**Markets:** {', '.join(p.markets)}",
        "",
    ]

    if result.warnings:
        lines.append("## Warnings")
        for w in result.warnings:
            lines.append(f"- ⚠️ {w}")
        lines.append("")

    if result.applicable_directives:
        lines.append("## Applicable Directives")
        lines.append("")
        lines.append("| Directive | Name | Scope |")
        lines.append("|---|---|---|")
        for d in result.applicable_directives:
            lines.append(f"| {d.short_name} ({d.id}) | {d.full_name} | {d.scope[:80]}... |")
        lines.append("")

    if result.checklist:
        lines.append("## Compliance Checklist")
        lines.append("")
        for item in result.checklist:
            icon = "🔴" if item.priority == "required" else "🟡" if item.priority == "recommended" else "⚪"
            cost = f" ({item.estimated_cost})" if item.estimated_cost else ""
            lines.append(f"- {icon} **{item.directive_id}**: {item.action}{cost}")
        lines.append("")

    if result.risk_notes:
        lines.append("## Risk Notes")
        for note in result.risk_notes:
            lines.append(f"- {note}")
        lines.append("")

    print("\n".join(lines))


@click.group()
def cli():
    """Compliance Navigator – regulatory guidance for hardware builders."""
    pass


@cli.command()
@click.option("--file", "-f", "file_path", help="Path to product definition YAML file")
@click.option("--product-type", "-t", multiple=True, help="Product type(s)")
@click.option("--market", "-m", multiple=True, help="Target market(s): EU, US")
@click.option("--format", "output_format", default="rich", type=click.Choice(["rich", "json", "markdown"]))
def check(file_path, product_type, market, output_format):
    """Check compliance requirements for a product."""
    if file_path:
        product = load_product_from_yaml(file_path)
    elif product_type:
        product = Product(
            name="Quick Check",
            types=list(product_type),
            markets=list(market) if market else ["EU"],
        )
    else:
        console.print("[red]Error: Provide --file or --product-type[/red]")
        sys.exit(1)

    result = check_compliance(product)

    if output_format == "json":
        _render_json(result)
    elif output_format == "markdown":
        _render_markdown(result)
    else:
        _render_rich(result)


@cli.command("list-directives")
def list_directives():
    """List all directives in the database."""
    from .navigator import _get_directives

    table = Table(title="EU Directives Database")
    table.add_column("ID", style="bold")
    table.add_column("Short Name", style="cyan")
    table.add_column("Full Name")

    for d in _get_directives():
        table.add_row(d.id, d.short_name, d.full_name)

    console.print(table)


@cli.command("list-categories")
def list_categories():
    """List supported product categories."""
    from .navigator import _get_standard_map

    smap = _get_standard_map()
    table = Table(title="Supported Product Categories")
    table.add_column("Category", style="bold")
    table.add_column("Description")
    table.add_column("EU Directives", width=30)

    for cat_name, cat_data in smap.get("categories", {}).items():
        directives = ", ".join(cat_data.get("eu_directives", []))
        table.add_row(cat_name, cat_data.get("description", ""), directives[:60])

    console.print(table)


@cli.command()
@click.option("--category", "-c", help="Filter by category")
@click.option("--limit", "-n", default=20, help="Number of recalls to show")
def recalls(category, limit):
    """Search the recall database."""
    from .navigator import _get_recalls

    all_recalls = _get_recalls()

    if category:
        filtered = [r for r in all_recalls if r.category == category]
    else:
        filtered = all_recalls

    filtered.sort(key=lambda r: r.date, reverse=True)

    table = Table(title=f"Recalls ({len(filtered)} total, showing {min(limit, len(filtered))})")
    table.add_column("Date", width=12)
    table.add_column("Product", width=30)
    table.add_column("Hazard", width=35)
    table.add_column("Category", width=15)

    for r in filtered[:limit]:
        table.add_row(
            r.date[:10] if r.date else "–",
            r.product_name[:28] + "..." if len(r.product_name) > 30 else r.product_name,
            r.hazard[:33] + "..." if len(r.hazard) > 35 else r.hazard,
            r.category,
        )

    console.print(table)
    console.print(f"\n  Total recalls in database: {len(all_recalls)}")
    if category:
        console.print(f"  Filtered to category: {category} ({len(filtered)} recalls)")


if __name__ == "__main__":
    cli()
