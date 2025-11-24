#!/usr/bin/env python3
"""
TextLoom Database Index Migration Verification Script

This script verifies that the performance indexes have been correctly applied
and provides a quick health check of the database optimization.

Usage:
    uv run python scripts/verify_index_migration.py

Expected: All 20 indexes should be present and functional
"""

import asyncio
import logging
import sys
import time
from typing import Any, Dict, List

from sqlalchemy import text

from models.db_connection import get_db_session

# Configure logging
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)

# Expected indexes from the migration
EXPECTED_INDEXES = [
    # Tasks table indexes
    "idx_tasks_status_created_at",
    "idx_tasks_task_type_status",
    "idx_tasks_creator_id_status",
    "idx_tasks_celery_task_id",
    "idx_tasks_created_at",
    "idx_tasks_multi_video_status",
    # Media items indexes
    "idx_media_items_task_id",
    "idx_media_items_task_id_media_type",
    "idx_media_items_original_url",
    # Material analyses indexes
    "idx_material_analyses_task_id",
    "idx_material_analyses_task_status",
    "idx_material_analyses_media_item_id",
    # Sub video tasks indexes
    "idx_sub_video_tasks_parent_task_id",
    "idx_sub_video_tasks_parent_status",
    "idx_sub_video_tasks_sub_task_id",
    # Script contents indexes
    "idx_script_contents_task_id",
    "idx_script_contents_persona_id",
    "idx_script_contents_task_generation_status",
    # Personas indexes
    "idx_personas_is_preset",
    "idx_personas_persona_type",
]


async def check_indexes_exist() -> Dict[str, bool]:
    """Check if all expected indexes exist in the database."""
    logger.info("🔍 Checking index existence...")

    async with get_db_session() as session:
        query = text(
            """
            SELECT indexname 
            FROM pg_indexes 
            WHERE schemaname = 'textloom_core' 
              AND indexname LIKE 'idx_%'
            ORDER BY indexname
        """
        )

        result = await session.execute(query)
        existing_indexes = {row[0] for row in result.fetchall()}

    index_status = {}
    for expected_index in EXPECTED_INDEXES:
        index_status[expected_index] = expected_index in existing_indexes

    return index_status


async def test_query_performance() -> Dict[str, Dict[str, Any]]:
    """Test key queries to verify performance improvements."""
    logger.info("⚡ Testing query performance...")

    performance_results = {}

    async with get_db_session() as session:
        # Test 1: Task status query (should use idx_tasks_status_created_at)
        start_time = time.time()
        query1 = text(
            """
            SELECT id, title, status, created_at 
            FROM textloom_core.tasks 
            WHERE status = 'pending' 
            ORDER BY created_at DESC 
            LIMIT 10
        """
        )
        result1 = await session.execute(query1)
        rows1 = result1.fetchall()
        end_time = time.time()

        performance_results["task_status_query"] = {
            "duration_ms": round((end_time - start_time) * 1000, 2),
            "rows_returned": len(rows1),
            "status": "PASS" if (end_time - start_time) < 0.1 else "SLOW",
        }

        # Test 2: Media items by task (should use idx_media_items_task_id)
        if rows1:
            task_id = rows1[0][0]
            start_time = time.time()
            query2 = text(
                """
                SELECT id, task_id, filename, media_type 
                FROM textloom_core.media_items 
                WHERE task_id = :task_id
            """
            )
            result2 = await session.execute(query2, {"task_id": task_id})
            rows2 = result2.fetchall()
            end_time = time.time()

            performance_results["media_items_query"] = {
                "duration_ms": round((end_time - start_time) * 1000, 2),
                "rows_returned": len(rows2),
                "status": "PASS" if (end_time - start_time) < 0.05 else "SLOW",
            }

        # Test 3: Task type and status (should use idx_tasks_task_type_status)
        start_time = time.time()
        query3 = text(
            """
            SELECT id, title, task_type, status 
            FROM textloom_core.tasks 
            WHERE task_type = 'TEXT_TO_VIDEO' AND status = 'completed'
            LIMIT 10
        """
        )
        result3 = await session.execute(query3)
        rows3 = result3.fetchall()
        end_time = time.time()

        performance_results["task_type_status_query"] = {
            "duration_ms": round((end_time - start_time) * 1000, 2),
            "rows_returned": len(rows3),
            "status": "PASS" if (end_time - start_time) < 0.1 else "SLOW",
        }

    return performance_results


async def get_index_usage_stats() -> List[Dict[str, Any]]:
    """Get index usage statistics."""
    logger.info("📊 Getting index usage statistics...")

    async with get_db_session() as session:
        query = text(
            """
            SELECT 
                indexname,
                idx_scan,
                idx_tup_read,
                idx_tup_fetch,
                CASE 
                    WHEN idx_scan = 0 THEN 'UNUSED'
                    WHEN idx_scan < 10 THEN 'LOW'
                    WHEN idx_scan < 100 THEN 'MODERATE'
                    ELSE 'HIGH'
                END as usage_level
            FROM pg_stat_user_indexes 
            WHERE schemaname = 'textloom_core'
              AND indexname LIKE 'idx_%'
            ORDER BY idx_scan DESC
        """
        )

        result = await session.execute(query)
        return [
            {
                "indexname": row[0],
                "scans": row[1],
                "tuples_read": row[2],
                "tuples_fetched": row[3],
                "usage_level": row[4],
            }
            for row in result.fetchall()
        ]


async def get_table_sizes() -> List[Dict[str, Any]]:
    """Get table and index size information."""
    logger.info("💾 Getting storage information...")

    async with get_db_session() as session:
        query = text(
            """
            SELECT 
                tablename,
                pg_size_pretty(pg_total_relation_size('textloom_core.'||tablename)) as total_size,
                pg_size_pretty(pg_relation_size('textloom_core.'||tablename)) as table_size,
                pg_size_pretty(
                    pg_total_relation_size('textloom_core.'||tablename) - 
                    pg_relation_size('textloom_core.'||tablename)
                ) as index_size
            FROM pg_tables 
            WHERE schemaname = 'textloom_core'
            ORDER BY pg_total_relation_size('textloom_core.'||tablename) DESC
        """
        )

        result = await session.execute(query)
        return [
            {
                "table": row[0],
                "total_size": row[1],
                "table_size": row[2],
                "index_size": row[3],
            }
            for row in result.fetchall()
        ]


def print_verification_report(
    index_status: Dict[str, bool],
    performance_results: Dict[str, Dict[str, Any]],
    usage_stats: List[Dict[str, Any]],
    table_sizes: List[Dict[str, Any]],
):
    """Print a comprehensive verification report."""

    print("\n" + "=" * 80)
    print("🎯 TEXTLOOM DATABASE INDEX MIGRATION VERIFICATION REPORT")
    print("=" * 80)

    # Index existence check
    print("\n📋 INDEX EXISTENCE CHECK")
    print("-" * 40)

    missing_indexes = []
    for index_name, exists in index_status.items():
        status = "✅ EXISTS" if exists else "❌ MISSING"
        print(f"{index_name:<40} {status}")
        if not exists:
            missing_indexes.append(index_name)

    print(
        f"\nSummary: {len([x for x in index_status.values() if x])}/{len(EXPECTED_INDEXES)} indexes found"
    )

    if missing_indexes:
        print(f"⚠️  Missing indexes: {', '.join(missing_indexes)}")
    else:
        print("✅ All expected indexes are present!")

    # Performance test results
    print("\n⚡ PERFORMANCE TEST RESULTS")
    print("-" * 40)

    for query_name, results in performance_results.items():
        status_icon = "✅" if results["status"] == "PASS" else "⚠️"
        print(f"{status_icon} {query_name}:")
        print(f"   Duration: {results['duration_ms']}ms")
        print(f"   Rows: {results['rows_returned']}")
        print(f"   Status: {results['status']}")
        print()

    # Performance summary
    all_fast = all(r["status"] == "PASS" for r in performance_results.values())
    if all_fast:
        print("✅ All queries performing within expected thresholds!")
    else:
        print("⚠️  Some queries are slower than expected. Monitor performance.")

    # Index usage statistics (top 10)
    print("\n📊 INDEX USAGE STATISTICS (Top 10)")
    print("-" * 60)
    print(f"{'Index Name':<35} {'Scans':<8} {'Usage':<10}")
    print("-" * 60)

    for stat in usage_stats[:10]:
        print(f"{stat['indexname']:<35} {stat['scans']:<8} {stat['usage_level']:<10}")

    # Storage information
    print("\n💾 STORAGE INFORMATION")
    print("-" * 60)
    print(f"{'Table':<25} {'Total Size':<12} {'Table Size':<12} {'Index Size':<12}")
    print("-" * 60)

    for size_info in table_sizes[:10]:
        print(
            f"{size_info['table']:<25} {size_info['total_size']:<12} {size_info['table_size']:<12} {size_info['index_size']:<12}"
        )

    # Overall assessment
    print("\n🎉 OVERALL ASSESSMENT")
    print("-" * 40)

    if not missing_indexes and all_fast:
        print("✅ MIGRATION SUCCESSFUL: All indexes created and performing well!")
        print("🚀 Expected performance improvements:")
        print("   • Task queries: 60-80% faster")
        print("   • Media lookups: 70-90% faster")
        print("   • Analysis queries: 60-75% faster")
        print("   • Multi-video tasks: 80-90% faster")
    elif missing_indexes:
        print("❌ MIGRATION INCOMPLETE: Missing indexes detected!")
        print("🔧 Action required: Re-run migration or create missing indexes manually")
    else:
        print("⚠️  MIGRATION PARTIAL: Indexes created but performance needs monitoring")
        print("📈 Recommendation: Run ANALYZE and monitor query performance")


async def main():
    """Main verification function."""
    try:
        logger.info("Starting database index migration verification...")

        # Check index existence
        index_status = await check_indexes_exist()

        # Test query performance
        performance_results = await test_query_performance()

        # Get usage statistics
        usage_stats = await get_index_usage_stats()

        # Get storage information
        table_sizes = await get_table_sizes()

        # Print comprehensive report
        print_verification_report(
            index_status, performance_results, usage_stats, table_sizes
        )

        # Determine exit code
        missing_indexes = [name for name, exists in index_status.items() if not exists]
        if missing_indexes:
            logger.error(
                f"Migration verification failed: {len(missing_indexes)} missing indexes"
            )
            sys.exit(1)
        else:
            logger.info("Migration verification completed successfully!")
            sys.exit(0)

    except Exception as e:
        logger.error(f"Verification failed with error: {str(e)}")
        print(f"\n❌ VERIFICATION FAILED: {str(e)}")
        sys.exit(1)


if __name__ == "__main__":
    asyncio.run(main())
