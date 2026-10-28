# OWNEX Performance Guide

## Benchmarks

### Startup Time
- **App import**: 2.57s (FastAPI + all routers)
- **Database init**: 6ms (SQLite with WAL mode)
- **First query**: 6ms (targets table)

### API Endpoints
- **Health**: 33ms
- **Overview**: 1.6ms (401 without auth)
- **Financial state**: 1.2ms (401 without auth)

### Frontend Build
- **Build time**: 12.14s
- **Bundle size**: 456KB (index-CYZT8j-J.js)
- **Gzipped**: 148KB

### Memory Usage
- **Python process**: 13.73MB
- **SQLAlchemy pool**: 5 connections

## Database Optimization

### SQLite Configuration
```python
# PRAGMA settings for performance
PRAGMA busy_timeout=5000
PRAGMA journal_mode=WAL
PRAGMA synchronous=NORMAL
PRAGMA foreign_keys=ON
```

### Query Optimization

#### ❌ Bad: Unbounded queries
```python
targets = session.query(Target).all()
endpoints = session.query(Endpoint).all()
findings = session.query(Finding).all()
```

#### ✅ Good: Bounded queries with limits
```python
targets = session.query(Target).limit(100).all()
target_ids = [t.id for t in targets]
endpoints = session.query(Endpoint).filter(Endpoint.target_id.in_(target_ids)).limit(500).all()
```

### Index Strategy
```sql
-- Core indexes for performance
CREATE INDEX ix_targets_name ON targets (name);
CREATE INDEX ix_endpoints_target_id ON endpoints (target_id);
CREATE INDEX ix_findings_target_id ON findings (target_id);
CREATE INDEX ix_findings_endpoint_id ON findings (endpoint_id);
CREATE INDEX ix_memory_records_category ON memory_records (category);
CREATE INDEX ix_memory_records_key ON memory_records (key);
```

## API Performance

### Response Time Targets
| Endpoint | Target | Current |
|----------|--------|---------|
| Health | <50ms | 33ms ✅ |
| Overview | <100ms | 1.6ms ✅ |
| Financial | <100ms | 1.2ms ✅ |
| Findings | <200ms | TBD |
| Reports | <200ms | TBD |

### Optimization Techniques

1. **Connection Pooling**: SQLAlchemy pool size 5
2. **Lazy Loading**: Load relationships only when needed
3. **Query Limits**: Always use `.limit()` for list queries
4. **Pagination**: Use `offset` + `limit` for large datasets
5. **Caching**: Redis/Memcached for frequently accessed data

## Frontend Performance

### Bundle Optimization
- **Code splitting**: Dynamic imports for routes
- **Tree shaking**: Remove unused code
- **Compression**: Gzip enabled

### Load Time Targets
| Metric | Target | Current |
|--------|--------|---------|
| First Contentful Paint | <1.5s | TBD |
| Largest Contentful Paint | <2.5s | TBD |
| Time to Interactive | <3.5s | TBD |

### Optimization Techniques

1. **Lazy Loading**: Load components on demand
2. **Virtual Scrolling**: For large lists
3. **Debouncing**: For search/filter inputs
4. **Memoization**: Cache computed values
5. **Image Optimization**: WebP format, lazy loading

## Desktop Performance

### Startup Time
- **PyInstaller bundle**: ~2-3s
- **Tauri bundle**: ~1-2s

### Memory Usage
- **Target**: <100MB
- **Current**: ~50MB (estimated)

## Monitoring

### Metrics to Track
1. **API response times** (p50, p95, p99)
2. **Database query times**
3. **Memory usage**
4. **CPU usage**
5. **Error rates**

### Tools
- **Prometheus**: Metrics collection
- **Grafana**: Visualization
- **Sentry**: Error tracking

## Optimization Checklist

### Before Release
- [ ] Profile API endpoints
- [ ] Optimize slow queries
- [ ] Add database indexes
- [ ] Enable caching
- [ ] Compress frontend assets
- [ ] Test with production data
- [ ] Load test critical paths

### Ongoing
- [ ] Monitor response times
- [ ] Track memory usage
- [ ] Review slow query logs
- [ ] Optimize based on usage patterns
