"""CLI entry point for the restaurant recommendation system."""

import argparse
import json
import logging
import sys
from pathlib import Path

from app.orchestrator import RecommendationOrchestrator
from data.models import BudgetTier, UserPreferences

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)


def parse_args() -> argparse.Namespace:
    """Parse command-line arguments."""
    parser = argparse.ArgumentParser(
        description="Get AI-powered restaurant recommendations from the Zomato dataset."
    )
    parser.add_argument(
        "--location",
        type=str,
        required=True,
        help="City or locality to search in (e.g., 'Delhi', 'Bangalore')",
    )
    parser.add_argument(
        "--budget",
        type=str,
        choices=["low", "medium", "high"],
        required=True,
        help="Budget tier: low, medium, or high",
    )
    parser.add_argument(
        "--cuisine",
        type=str,
        default="",
        help="Cuisine preference (comma-separated for multiple, e.g., 'Italian,Chinese')",
    )
    parser.add_argument(
        "--min-rating",
        type=float,
        default=0.0,
        help="Minimum restaurant rating (0.0 to 5.0, default: 0.0)",
    )
    parser.add_argument(
        "--top-n",
        type=int,
        default=5,
        help="Number of recommendations to return (default: 5)",
    )
    parser.add_argument(
        "--extras",
        type=str,
        default="",
        help="Extra keywords to search for (comma-separated, e.g., 'family-friendly,outdoor')",
    )
    parser.add_argument(
        "--json-file",
        type=str,
        help="Path to JSON file containing preferences (overrides other args)",
    )
    parser.add_argument(
        "--output-format",
        type=str,
        choices=["text", "json"],
        default="text",
        help="Output format: text or json (default: text)",
    )
    return parser.parse_args()


def load_preferences_from_json(file_path: str) -> UserPreferences:
    """Load user preferences from a JSON file."""
    path = Path(file_path)
    if not path.exists():
        raise FileNotFoundError(f"JSON file not found: {file_path}")

    with open(path) as f:
        data = json.load(f)

    return UserPreferences(
        location=data.get("location", ""),
        budget=BudgetTier(data.get("budget", "medium")),
        cuisine=data.get("cuisine", []),
        min_rating=data.get("min_rating", 0.0),
        extras=data.get("extras", []),
        top_n=data.get("top_n", 5),
    )


def format_text_output(response) -> str:
    """Format the recommendation response as human-readable text."""
    lines = []
    lines.append("=" * 60)
    lines.append("RESTAURANT RECOMMENDATIONS")
    lines.append("=" * 60)

    if response.message:
        lines.append(f"\n{response.message}\n")

    if not response.recommendations:
        lines.append("No recommendations found.")
        return "\n".join(lines)

    for rec in response.recommendations:
        r = rec.restaurant
        lines.append(f"\n#{rec.rank} - {r.name}")
        lines.append(f"  Location: {r.location}, {r.city}")
        lines.append(f"  Cuisines: {', '.join(r.cuisines)}")
        lines.append(f"  Rating: {r.rating}/5.0")
        if r.cost_for_two:
            lines.append(f"  Cost for two: ₹{r.cost_for_two}")
        lines.append(f"  Budget tier: {r.budget_tier.value}")
        lines.append(f"  Explanation: {rec.explanation}")
        if rec.match_highlights:
            lines.append(f"  Highlights: {', '.join(rec.match_highlights)}")

    # Add metadata section
    lines.append("\n" + "-" * 60)
    lines.append("METADATA")
    lines.append("-" * 60)
    lines.append(f"Total candidates: {response.metadata.total_candidates}")
    lines.append(f"AI explanations available: {response.metadata.ai_explanations_available}")
    if response.metadata.llm_attempts > 1:
        lines.append(f"LLM attempts: {response.metadata.llm_attempts}")
    if response.metadata.parse_used_fallback:
        lines.append("Parse fallback used: Yes")
    if response.metadata.stripped_invalid_ids > 0:
        lines.append(f"Stripped invalid IDs: {response.metadata.stripped_invalid_ids}")

    # Add filter stats if available
    if response.filter_stats:
        lines.append("\n" + "-" * 60)
        lines.append("FILTER STATS")
        lines.append("-" * 60)
        lines.append(f"Input count: {response.filter_stats.input_count}")
        lines.append(f"Output count: {response.filter_stats.output_count}")
        if response.filter_stats.capped_to:
            lines.append(f"Capped to: {response.filter_stats.capped_to}")
        if response.filter_stats.suggestions:
            lines.append("\nSuggestions:")
            for suggestion in response.filter_stats.suggestions:
                lines.append(f"  • {suggestion}")

    return "\n".join(lines)


def main() -> int:
    """Main CLI entry point."""
    args = parse_args()

    try:
        # Load preferences from JSON file or command-line args
        if args.json_file:
            logger.info("Loading preferences from JSON file: %s", args.json_file)
            preferences = load_preferences_from_json(args.json_file)
        else:
            preferences = UserPreferences(
                location=args.location,
                budget=BudgetTier(args.budget),
                cuisine=args.cuisine,
                min_rating=args.min_rating,
                extras=args.extras.split(",") if args.extras else [],
                top_n=args.top_n,
            )

        logger.info(
            "Generating recommendations for: location=%s, budget=%s, cuisine=%s, min_rating=%s, top_n=%s",
            preferences.location,
            preferences.budget.value,
            preferences.cuisine_list(),
            preferences.min_rating,
            preferences.top_n,
        )

        # Initialize orchestrator and get recommendations
        orchestrator = RecommendationOrchestrator()
        response = orchestrator.recommend(preferences)

        # Output results
        if args.output_format == "json":
            print(response.model_dump_json(indent=2))
        else:
            print(format_text_output(response))

        return 0

    except FileNotFoundError as e:
        logger.error("File not found: %s", e)
        print(f"Error: {e}", file=sys.stderr)
        return 1
    except ValueError as e:
        logger.error("Invalid input: %s", e)
        print(f"Error: {e}", file=sys.stderr)
        return 1
    except RuntimeError as e:
        logger.error("Runtime error: %s", e)
        print(f"Error: {e}", file=sys.stderr)
        return 1
    except Exception as e:
        logger.error("Unexpected error: %s", e, exc_info=True)
        print(f"Unexpected error: {e}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
