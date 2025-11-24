-- TextLoom Database Performance Validation Script
-- Purpose: Validate index effectiveness and measure query performance improvements
-- Usage: Run before and after applying the index migration for comparison

-- =============================================================================
-- PERFORMANCE TESTING SETUP
-- =============================================================================

-- Enable query execution plan analysis
\timing on
\set ECHO queries

-- Store test results
DROP TABLE IF EXISTS performance_test_results;
CREATE TEMPORARY TABLE performance_test_results (
    test_name VARCHAR(100),
    execution_time_ms NUMERIC,
    rows_returned INTEGER,
    index_used BOOLEAN,
    test_timestamp TIMESTAMP DEFAULT NOW()
);

-- =============================================================================
-- BASELINE PERFORMANCE TESTS (Run BEFORE index migration)
-- =============================================================================

\echo ''
\echo '=== BASELINE PERFORMANCE TESTS (BEFORE INDEXES) ==='
\echo ''

-- Test 1: Task status filtering with ordering (most common query)
\echo 'Test 1: Task status filtering with ordering'
EXPLAIN (ANALYZE, BUFFERS, FORMAT TEXT)
SELECT id, title, status, created_at, progress
FROM textloom_core.tasks 
WHERE status = 'processing' 
ORDER BY created_at DESC 
LIMIT 50;

-- Test 2: Media items by task_id (N+1 query bottleneck)
\echo 'Test 2: Media items by task_id lookup'
EXPLAIN (ANALYZE, BUFFERS, FORMAT TEXT)
SELECT id, task_id, filename, media_type, file_size
FROM textloom_core.media_items 
WHERE task_id = (SELECT id FROM textloom_core.tasks LIMIT 1);

-- Test 3: Material analyses by task_id
\echo 'Test 3: Material analyses by task_id'
EXPLAIN (ANALYZE, BUFFERS, FORMAT TEXT)
SELECT id, task_id, status, ai_description, quality_score
FROM textloom_core.material_analyses 
WHERE task_id = (SELECT id FROM textloom_core.tasks LIMIT 1);

-- Test 4: Task type and status filtering
\echo 'Test 4: Task type and status filtering'
EXPLAIN (ANALYZE, BUFFERS, FORMAT TEXT)
SELECT id, title, task_type, status, created_at
FROM textloom_core.tasks 
WHERE task_type = 'TEXT_TO_VIDEO' AND status = 'completed';

-- Test 5: Sub-video tasks by parent
\echo 'Test 5: Sub-video tasks by parent_task_id'
EXPLAIN (ANALYZE, BUFFERS, FORMAT TEXT)
SELECT id, parent_task_id, status, progress, video_url
FROM textloom_core.sub_video_tasks 
WHERE parent_task_id = (SELECT id FROM textloom_core.tasks WHERE is_multi_video_task = true LIMIT 1);

-- Test 6: Time-based task queries
\echo 'Test 6: Time-based task filtering'
EXPLAIN (ANALYZE, BUFFERS, FORMAT TEXT)
SELECT id, title, created_at, status
FROM textloom_core.tasks 
WHERE created_at >= NOW() - INTERVAL '24 hours'
ORDER BY created_at DESC;

-- Test 7: Celery task ID lookup
\echo 'Test 7: Celery task ID lookup'
EXPLAIN (ANALYZE, BUFFERS, FORMAT TEXT)
SELECT id, title, status, progress, celery_task_id
FROM textloom_core.tasks 
WHERE celery_task_id IS NOT NULL
LIMIT 10;

-- Test 8: Creator-based task filtering
\echo 'Test 8: Creator-based task filtering'
EXPLAIN (ANALYZE, BUFFERS, FORMAT TEXT)
SELECT id, title, creator_id, status, created_at
FROM textloom_core.tasks 
WHERE creator_id IS NOT NULL AND status IN ('pending', 'processing')
ORDER BY created_at DESC;

-- =============================================================================
-- POST-MIGRATION VALIDATION TESTS (Run AFTER index migration)
-- =============================================================================

\echo ''
\echo '=== POST-MIGRATION VALIDATION TESTS (AFTER INDEXES) ==='
\echo ''

-- Verify all new indexes were created
\echo 'Checking new indexes creation:'
SELECT 
    schemaname,
    tablename, 
    indexname,
    indexdef
FROM pg_indexes 
WHERE schemaname = 'textloom_core' 
  AND indexname LIKE 'idx_%'
ORDER BY tablename, indexname;

-- Test index usage for each critical query pattern
\echo ''
\echo 'Validating index usage for critical queries:'

-- Validation 1: Task status queries should use idx_tasks_status_created_at
\echo 'Validation 1: Task status + created_at index'
EXPLAIN (ANALYZE, BUFFERS, FORMAT TEXT)
SELECT id, title, status, created_at, progress
FROM textloom_core.tasks 
WHERE status = 'processing' 
ORDER BY created_at DESC 
LIMIT 50;

-- Validation 2: Media items should use idx_media_items_task_id
\echo 'Validation 2: Media items task_id index'
EXPLAIN (ANALYZE, BUFFERS, FORMAT TEXT)
SELECT id, task_id, filename, media_type
FROM textloom_core.media_items 
WHERE task_id = (SELECT id FROM textloom_core.tasks LIMIT 1);

-- Validation 3: Task type + status should use idx_tasks_task_type_status
\echo 'Validation 3: Task type + status composite index'
EXPLAIN (ANALYZE, BUFFERS, FORMAT TEXT)
SELECT id, title, task_type, status
FROM textloom_core.tasks 
WHERE task_type = 'TEXT_TO_VIDEO' AND status = 'completed';

-- Validation 4: Celery task ID should use idx_tasks_celery_task_id (hash index)
\echo 'Validation 4: Celery task ID hash index'
EXPLAIN (ANALYZE, BUFFERS, FORMAT TEXT)
SELECT id, celery_task_id, status
FROM textloom_core.tasks 
WHERE celery_task_id = (SELECT celery_task_id FROM textloom_core.tasks WHERE celery_task_id IS NOT NULL LIMIT 1);

-- Validation 5: Sub-video tasks should use idx_sub_video_tasks_parent_task_id
\echo 'Validation 5: Sub-video tasks parent_task_id index'
EXPLAIN (ANALYZE, BUFFERS, FORMAT TEXT)
SELECT id, parent_task_id, status, progress
FROM textloom_core.sub_video_tasks 
WHERE parent_task_id = (SELECT id FROM textloom_core.tasks WHERE is_multi_video_task = true LIMIT 1);

-- =============================================================================
-- PERFORMANCE COMPARISON QUERIES
-- =============================================================================

\echo ''
\echo '=== PERFORMANCE COMPARISON ANALYSIS ==='
\echo ''

-- Query to measure actual performance improvement
-- Run this with \timing on to measure execution times

\echo 'Performance Test Suite (measure execution times):'

-- Simulate typical application load pattern
DO $$
DECLARE 
    task_record RECORD;
    media_count INTEGER;
    analysis_count INTEGER;
    start_time TIMESTAMP;
    end_time TIMESTAMP;
    execution_ms NUMERIC;
BEGIN
    -- Test N+1 query resolution
    start_time := clock_timestamp();
    
    FOR task_record IN 
        SELECT id, title, status FROM textloom_core.tasks LIMIT 10
    LOOP
        SELECT COUNT(*) INTO media_count 
        FROM textloom_core.media_items 
        WHERE task_id = task_record.id;
        
        SELECT COUNT(*) INTO analysis_count 
        FROM textloom_core.material_analyses 
        WHERE task_id = task_record.id;
    END LOOP;
    
    end_time := clock_timestamp();
    execution_ms := EXTRACT(EPOCH FROM (end_time - start_time)) * 1000;
    
    RAISE NOTICE 'N+1 Query Test: % ms for 10 tasks', execution_ms;
END $$;

-- =============================================================================
-- INDEX USAGE STATISTICS
-- =============================================================================

\echo ''
\echo '=== INDEX USAGE STATISTICS ==='
\echo ''

-- Monitor index usage after migration
SELECT 
    schemaname,
    tablename,
    indexname,
    idx_scan as "Index Scans",
    idx_tup_read as "Tuples Read",
    idx_tup_fetch as "Tuples Fetched",
    CASE 
        WHEN idx_scan = 0 THEN 'UNUSED'
        WHEN idx_scan < 10 THEN 'LOW USAGE'
        WHEN idx_scan < 100 THEN 'MODERATE USAGE'
        ELSE 'HIGH USAGE'
    END as usage_level
FROM pg_stat_user_indexes 
WHERE schemaname = 'textloom_core'
  AND indexname LIKE 'idx_%'
ORDER BY idx_scan DESC;

-- =============================================================================
-- QUERY PERFORMANCE MONITORING
-- =============================================================================

\echo ''
\echo '=== SLOW QUERY ANALYSIS ==='
\echo ''

-- Identify slow queries (requires pg_stat_statements extension)
-- Run this periodically to monitor query performance
SELECT 
    SUBSTRING(query, 1, 80) as query_excerpt,
    calls,
    total_time,
    mean_time,
    CASE 
        WHEN mean_time > 1000 THEN 'CRITICAL'
        WHEN mean_time > 500 THEN 'WARNING'
        WHEN mean_time > 100 THEN 'WATCH'
        ELSE 'OK'
    END as performance_status
FROM pg_stat_statements 
WHERE query LIKE '%textloom_core%'
  AND calls > 5
ORDER BY mean_time DESC
LIMIT 20;

-- =============================================================================
-- TABLE AND INDEX SIZES
-- =============================================================================

\echo ''
\echo '=== STORAGE ANALYSIS ==='
\echo ''

-- Monitor table and index sizes
SELECT 
    schemaname,
    tablename,
    pg_size_pretty(pg_total_relation_size(schemaname||'.'||tablename)) as total_size,
    pg_size_pretty(pg_relation_size(schemaname||'.'||tablename)) as table_size,
    pg_size_pretty(pg_total_relation_size(schemaname||'.'||tablename) - pg_relation_size(schemaname||'.'||tablename)) as index_size,
    ROUND(
        (pg_total_relation_size(schemaname||'.'||tablename) - pg_relation_size(schemaname||'.'||tablename))::NUMERIC / 
        pg_relation_size(schemaname||'.'||tablename) * 100, 2
    ) as index_ratio_percent
FROM pg_tables 
WHERE schemaname = 'textloom_core'
ORDER BY pg_total_relation_size(schemaname||'.'||tablename) DESC;

-- Individual index sizes
SELECT 
    schemaname,
    tablename,
    indexname,
    pg_size_pretty(pg_relation_size(indexrelid)) as index_size
FROM pg_stat_user_indexes 
WHERE schemaname = 'textloom_core'
  AND indexname LIKE 'idx_%'
ORDER BY pg_relation_size(indexrelid) DESC;

-- =============================================================================
-- MAINTENANCE RECOMMENDATIONS
-- =============================================================================

\echo ''
\echo '=== MAINTENANCE RECOMMENDATIONS ==='
\echo ''

-- Check for index bloat
SELECT 
    schemaname,
    tablename,
    indexname,
    pg_size_pretty(pg_relation_size(indexrelid)) as current_size,
    CASE 
        WHEN pg_relation_size(indexrelid) > 50 * 1024 * 1024 THEN 'Consider REINDEX'
        WHEN pg_relation_size(indexrelid) > 10 * 1024 * 1024 THEN 'Monitor growth'
        ELSE 'OK'
    END as maintenance_status
FROM pg_stat_user_indexes 
WHERE schemaname = 'textloom_core'
ORDER BY pg_relation_size(indexrelid) DESC;

-- Vacuum and analyze recommendations
SELECT 
    schemaname,
    tablename,
    n_tup_ins + n_tup_upd + n_tup_del as total_modifications,
    CASE 
        WHEN last_vacuum IS NULL THEN 'VACUUM NEEDED'
        WHEN last_vacuum < NOW() - INTERVAL '7 days' THEN 'VACUUM RECOMMENDED'
        ELSE 'OK'
    END as vacuum_status,
    CASE 
        WHEN last_analyze IS NULL THEN 'ANALYZE NEEDED'
        WHEN last_analyze < NOW() - INTERVAL '7 days' THEN 'ANALYZE RECOMMENDED'
        ELSE 'OK'
    END as analyze_status
FROM pg_stat_user_tables 
WHERE schemaname = 'textloom_core'
ORDER BY n_tup_ins + n_tup_upd + n_tup_del DESC;

\echo ''
\echo '=== PERFORMANCE VALIDATION COMPLETE ==='
\echo ''
\echo 'Expected improvements after index migration:'
\echo '- Task status queries: 60-80% faster'
\echo '- Media items lookup: 70-90% faster'
\echo '- Material analyses: 60-75% faster'
\echo '- Sub-video tasks: 80-90% faster'
\echo '- Overall throughput: 40-60% improvement'
\echo ''