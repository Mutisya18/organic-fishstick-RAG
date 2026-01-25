# Maintenance and Operations Guide

**RAG Chatbot with Eligibility Module**  
**Version**: 1.0 | **Status**: Production Ready ✅

---

## Table of Contents

1. [Daily Operations](#daily-operations)
2. [Monitoring & Health Checks](#monitoring--health-checks)
3. [Incident Response](#incident-response)
4. [Troubleshooting by Scenario](#troubleshooting-by-scenario)
5. [Performance Tuning](#performance-tuning)
6. [Maintenance Schedules](#maintenance-schedules)
7. [Backup & Recovery](#backup--recovery)
8. [Operational Runbooks](#operational-runbooks)
9. [Checklists](#checklists)

---

## Daily Operations

### Morning Startup Checklist

**Time: 5-10 minutes**

```bash
# 1. Check system resources
free -h                    # RAM available?
df -h /                    # Disk space >1GB?
ps aux | grep ollama       # Ollama running?
ps aux | grep streamlit    # Streamlit running?

# 2. Start services (if needed)
# Terminal 1: Start Ollama
ollama serve

# Terminal 2: Start Streamlit
cd /workspaces/organic-fishstick-RAG
source venv/bin/activate
streamlit run app.py

# 3. Verify connectivity
curl http://localhost:11434/api/tags    # Ollama OK?
curl http://localhost:8501 > /dev/null  # Streamlit OK?

# 4. Check logs for errors
tail -50 logs/session_*.log | grep ERROR

# 5. Verify databases
ls -lh eligibility/data/*.xlsx          # Data files exist?
ls -lh chroma/                          # Vector DB exists?
```

**Checklist**:
- [ ] Free RAM > 2GB
- [ ] Free disk > 1GB
- [ ] Ollama running (port 11434)
- [ ] Streamlit running (port 8501)
- [ ] No ERROR in recent logs
- [ ] Data files readable
- [ ] Vector database present

### Evening Shutdown Checklist

**Time: 2-3 minutes**

```bash
# 1. Check for pending operations
ps aux | grep -E "streamlit|ollama"

# 2. Review error logs
grep ERROR logs/session_*.log | tail -20

# 3. Compact logs (optional)
gzip logs/session_*.log.* 2>/dev/null || true

# 4. Stop services gracefully
# Terminal running Streamlit: Ctrl+C
# Terminal running Ollama: Ctrl+C

# 5. Verify stopped
ps aux | grep -E "streamlit|ollama" | grep -v grep
```

### Session Monitoring

```bash
# Monitor active sessions
watch -n 5 'ls -lt logs/ | head -10'

# Track user queries
tail -f logs/session_*.log | jq '.query' | head -20

# Count transactions per session
jq '.request_id' logs/session_*.log | sort | uniq -c | sort -nr | head -10
```

---

## Monitoring & Health Checks

### System Health Dashboard

```bash
#!/bin/bash
# health_check.sh

echo "=== System Health Check ==="
echo ""

echo "1. System Resources:"
free -h | grep Mem
df -h / | tail -1
uptime

echo ""
echo "2. Service Status:"
curl -s http://localhost:11434/api/tags > /dev/null && echo "✅ Ollama: OK" || echo "❌ Ollama: DOWN"
curl -s http://localhost:8501 > /dev/null && echo "✅ Streamlit: OK" || echo "❌ Streamlit: DOWN"

echo ""
echo "3. Data Integrity:"
file eligibility/data/*.xlsx | grep -c "Microsoft" && echo "✅ Excel files: OK" || echo "❌ Excel files: CORRUPTED"

echo ""
echo "4. Recent Errors (last 24h):"
find logs -mtime -1 -exec grep ERROR {} \; | wc -l

echo ""
echo "5. Disk Usage:"
du -sh . logs chroma eligibility/data 2>/dev/null

echo ""
echo "=== Health Check Complete ==="
```

**Run it**:
```bash
bash health_check.sh
```

### Performance Metrics

```bash
# Track response times
tail -100 logs/session_*.log | jq '.latency_ms | values' | python -c "
import sys, statistics
times = [int(x) for x in sys.stdin]
print(f'Min: {min(times)}ms, Max: {max(times)}ms, Avg: {statistics.mean(times):.0f}ms, P95: {sorted(times)[int(len(times)*0.95)]}ms')
"

# Count query types
tail -200 logs/session_*.log | jq '.query_type' | sort | uniq -c | sort -nr

# Error rate
total=$(tail -1000 logs/session_*.log | wc -l)
errors=$(tail -1000 logs/session_*.log | grep ERROR | wc -l)
echo "Error rate: $((errors * 100 / total))%"

# Session volume
ls logs/session_*.log | wc -l
```

### Automated Health Monitoring

```python
# monitor.py - Run via cron

import os
import json
from datetime import datetime, timedelta
import subprocess

def check_health():
    issues = []
    
    # Check disk
    result = subprocess.run(['df', '/'], capture_output=True, text=True)
    usage = float(result.stdout.split('\n')[1].split()[4].rstrip('%'))
    if usage > 90:
        issues.append(f"Disk usage critical: {usage}%")
    
    # Check Ollama
    try:
        subprocess.run(['curl', '-s', 'http://localhost:11434/api/tags'],
                      timeout=2, check=True, capture_output=True)
    except:
        issues.append("Ollama not responding")
    
    # Check Streamlit
    try:
        subprocess.run(['curl', '-s', 'http://localhost:8501'],
                      timeout=2, check=True, capture_output=True)
    except:
        issues.append("Streamlit not responding")
    
    # Check recent errors
    log_dir = 'logs'
    hour_ago = datetime.now() - timedelta(hours=1)
    error_count = 0
    for f in os.listdir(log_dir):
        fpath = os.path.join(log_dir, f)
        if os.path.getmtime(fpath) > hour_ago.timestamp():
            with open(fpath) as fp:
                error_count += sum(1 for line in fp if 'ERROR' in line)
    
    if error_count > 10:
        issues.append(f"{error_count} errors in last hour")
    
    return issues

if __name__ == '__main__':
    issues = check_health()
    if issues:
        print("⚠️  Health Issues Found:")
        for issue in issues:
            print(f"  - {issue}")
    else:
        print("✅ System healthy")
```

**Run on schedule**:
```bash
# Add to crontab (every 30 minutes)
*/30 * * * * cd /workspaces/organic-fishstick-RAG && python monitor.py
```

---

## Incident Response

### Quick Response Procedures

#### Ollama Not Responding

**Symptom**: "Error connecting to localhost:11434"

```bash
# 1. Check if running
ps aux | grep ollama | grep -v grep

# 2. If running, restart
pkill ollama
sleep 2
ollama serve &

# 3. If port in use
lsof -i :11434
kill -9 <PID>
ollama serve &

# 4. Verify
curl http://localhost:11434/api/tags
```

**Time to recovery**: 30 seconds - 2 minutes

#### Streamlit Crashed

**Symptom**: "Connection refused" on port 8501

```bash
# 1. Check process
ps aux | grep streamlit | grep -v grep

# 2. Restart
pkill streamlit
sleep 2
cd /workspaces/organic-fishstick-RAG
source venv/bin/activate
streamlit run app.py &

# 3. Verify
curl http://localhost:8501
```

**Time to recovery**: 10-20 seconds

#### High Memory Usage

**Symptom**: System slowing down, "Out of memory" errors

```bash
# 1. Check memory
free -h
top -b -o %MEM | head -20

# 2. Identify largest processes
ps aux --sort=-%mem | head -5

# 3. Restart services (most common cause)
pkill -f streamlit
pkill -f ollama
sleep 5
ollama serve &
streamlit run app.py &

# 4. If still high, reduce model size
ollama pull tinyllama  # Smaller model
# Update get_embedding_function.py to use tinyllama
```

**Time to recovery**: 2-5 minutes

#### Disk Full

**Symptom**: "No space left on device"

```bash
# 1. Check usage
df -h
du -sh logs chroma eligibility/data

# 2. Clean old logs (keep last 30 days)
find logs -mtime +30 -delete

# 3. Compress old logs
gzip logs/*.log.* 2>/dev/null || true

# 4. Verify space
df -h /
```

**Time to recovery**: 1-3 minutes

#### Database Corruption

**Symptom**: "Invalid vector database" or "Chroma error"

```bash
# 1. Backup current database
mv chroma chroma.backup

# 2. Rebuild from PDFs
python populate_database.py

# 3. Verify
python -c "
import chromadb
client = chromadb.PersistentClient(path='chroma')
collection = client.get_or_create_collection(name='documents')
print(f'✅ Database OK, {collection.count()} vectors')
"

# 4. If rebuild fails, restore backup
rm -rf chroma
mv chroma.backup chroma
```

**Time to recovery**: 5-30 minutes (depends on PDF size)

### Incident Log Template

Keep incident records for analysis:

```json
{
  "incident_id": "INC-2024-001",
  "timestamp": "2024-01-15T10:30:00Z",
  "severity": "HIGH|MEDIUM|LOW",
  "service": "ollama|streamlit|database|system",
  "issue": "Brief description",
  "duration_minutes": 15,
  "root_cause": "Why it happened",
  "resolution": "How it was fixed",
  "prevention": "How to prevent next time",
  "impact": "Number of users/queries affected"
}
```

---

## Troubleshooting by Scenario

### Scenario 1: Eligibility Checks Not Working

**Symptoms**:
- "Module initialization failed"
- "Cannot load config"
- Eligibility queries return errors

**Diagnosis**:
```bash
# 1. Check config files valid
python -c "
import json
files = [
    'eligibility/config/checks_catalog.json',
    'eligibility/config/reason_detection_rules.json',
    'eligibility/config/reason_playbook.json'
]
for f in files:
    try:
        with open(f) as fp:
            json.load(fp)
        print(f'✅ {f}: Valid')
    except Exception as e:
        print(f'❌ {f}: {e}')
"

# 2. Check data files
ls -la eligibility/data/*.xlsx

# 3. Test module
python -c "
from eligibility.orchestrator import EligibilityOrchestrator
orch = EligibilityOrchestrator()
result = orch.process_query('Is account 1234567890 eligible?')
print(result)
"
```

**Solutions**:

| Issue | Fix |
|-------|-----|
| Config parse error | Validate JSON: `python -m json.tool eligibility/config/checks_catalog.json` |
| Data file not found | Create: `touch eligibility/data/eligible_customers.xlsx` |
| Module import error | Reinstall: `pip install -r requirements.txt --force-reinstall` |
| Incorrect result | Check data file schema matches expected columns |

### Scenario 2: RAG Queries Returning Empty Results

**Symptoms**:
- No documents returned
- "Vector database error"
- Irrelevant results

**Diagnosis**:
```bash
# 1. Check if PDFs exist
ls -la data/*.pdf

# 2. Check database has vectors
python -c "
import chromadb
client = chromadb.PersistentClient(path='chroma')
collection = client.get_or_create_collection(name='documents')
print(f'Vectors in database: {collection.count()}')
print(f'Documents: {collection.get()[:3]}')  # First 3
"

# 3. Test a simple query
python query_data.py "loan"
```

**Solutions**:

| Issue | Fix |
|-------|-----|
| No PDFs in data/ | Copy PDFs: `cp /path/*.pdf data/` |
| Database empty | Run: `python populate_database.py` |
| Database corrupted | Rebuild: `rm -rf chroma && python populate_database.py` |
| Poor results | Adjust k value in query_data.py (increase from 3 to 5) |
| Out of memory | Reduce chunk size: `chunk_size=400` in populate_database.py |

### Scenario 3: Slow Response Times

**Symptoms**:
- Queries taking 5+ seconds
- UI freezing
- Timeouts

**Diagnosis**:
```bash
# 1. Check system resources
free -h
top -b | head -20

# 2. Check network latency to Ollama
time curl http://localhost:11434/api/tags

# 3. Analyze query logs
tail -100 logs/session_*.log | jq '.latency_ms | values' | python3 -c "
import sys, statistics
times = [int(x) for x in sys.stdin.read().split() if x.isdigit()]
if times:
    print(f'P50: {sorted(times)[len(times)//2]}ms')
    print(f'P95: {sorted(times)[int(len(times)*0.95)]}ms')
    print(f'P99: {sorted(times)[int(len(times)*0.99)]}ms')
"
```

**Solutions**:

| Cause | Fix |
|-------|-----|
| Low RAM | Restart services: `pkill -f streamlit; pkill -f ollama` |
| Large model | Use smaller: `ollama pull tinyllama` |
| Network latency | Check: `ping localhost` (should be <2ms) |
| Slow embeddings | Use `nomic-embed-text` (fastest) |
| Many PDFs | Reduce chunk_size or k value |

### Scenario 4: Permission Errors

**Symptoms**:
- "Permission denied"
- "Cannot write to logs"
- "Cannot read from data"

**Diagnosis**:
```bash
# Check file permissions
ls -la logs/
ls -la eligibility/data/
ls -la chroma/

# Check user ownership
stat eligibility/data/eligible_customers.xlsx
```

**Solutions**:
```bash
# Fix ownership
sudo chown $USER:$USER -R .

# Fix permissions
chmod 755 logs
chmod 755 eligibility/data
chmod 644 logs/*
chmod 644 eligibility/data/*

# Test write access
touch logs/test.log && rm logs/test.log && echo "✅ OK"
```

### Scenario 5: Model Download Fails

**Symptoms**:
- "Error downloading model"
- "Connection timeout"
- Partial model download

**Diagnosis**:
```bash
# Check internet connectivity
ping 8.8.8.8

# Check already downloaded models
ollama list

# Check disk space
df -h /
```

**Solutions**:
```bash
# Retry download
ollama pull nomic-embed-text

# If timeout, download in chunks:
# 1. Check progress
ollama list

# 2. Resume (Ollama will auto-resume)
ollama pull nomic-embed-text

# If still failing:
# 1. Use mirror/alternate
# 2. Download manually and import
# 3. Use pre-downloaded file
```

---

## Performance Tuning

### Optimize Embedding Generation

```python
# In get_embedding_function.py
from langchain_community.embeddings.ollama import OllamaEmbeddings

embeddings = OllamaEmbeddings(
    model="nomic-embed-text",  # Fast, accurate
    base_url="http://localhost:11434",
    # num_gpu=1,  # Enable GPU if available
    # num_thread=4,  # Adjust based on CPU cores
)
```

### Optimize LLM Generation

```python
# In llm_payload_builder.py
from langchain_community.llms.ollama import Ollama

llm = Ollama(
    model="llama3.2:3b",  # ~2GB, good balance
    base_url="http://localhost:11434",
    temperature=0.1,  # Lower = more focused responses
    top_p=0.9,  # Controls diversity
    num_predict=150,  # Max tokens (lower = faster)
    # num_gpu=1,  # Enable GPU if available
)
```

### Optimize Chroma Vector Search

```python
# In query_data.py
k = 3  # Number of results (lower = faster)
fetch_k = 10  # Search depth (lower = faster)
lambda_mult = 0.25  # MMR weighting

# For slow queries, reduce k:
# k=5 → k=3: ~40% faster
# k=3 → k=1: ~50% faster (but less comprehensive)
```

### Database Optimization

```bash
# Analyze database
sqlite3 chroma.db
> SELECT COUNT(*) FROM embeddings;  # Total vectors
> SELECT AVG(LENGTH(embedding)) FROM embeddings;  # Avg size
> .quit

# Compact database
sqlite3 chroma.db VACUUM;

# Check fragmentation
sqlite3 chroma.db
> PRAGMA freelist_count;
```

### Caching Strategy

```python
# Add request caching (in app.py)
from functools import lru_cache
import hashlib

@lru_cache(maxsize=128)
def cached_query(query_hash):
    """Cache query results for 1 hour"""
    # Implementation
    pass

# Hash queries for caching
def get_query_hash(query):
    return hashlib.md5(query.lower().encode()).hexdigest()
```

---

## Maintenance Schedules

### Daily Maintenance (5 minutes)

- [ ] Morning startup checklist
- [ ] Verify no ERRORs in logs
- [ ] Check disk space >1GB
- [ ] Evening shutdown checklist

### Weekly Maintenance (30 minutes)

**Every Monday morning**:

```bash
# 1. Clean old logs (keep 7 days)
find logs -mtime +7 -delete

# 2. Analyze performance
tail -500 logs/session_*.log | jq '.latency_ms' | python3 -c "
import sys, statistics
times = [float(x) for x in sys.stdin if x.strip()]
if times:
    print(f'Weekly avg latency: {statistics.mean(times):.0f}ms')
    print(f'Weekly max latency: {max(times):.0f}ms')
    print(f'Weekly error rate: {???}%')
"

# 3. Verify data integrity
python -c "
import openpyxl
wb = openpyxl.load_workbook('eligibility/data/eligible_customers.xlsx')
print(f'✅ Eligible customers: {wb.active.max_row-1} rows')
"

# 4. Backup important files
tar -czf backups/config_backup_$(date +%Y%m%d).tar.gz eligibility/config/ 2>/dev/null || mkdir -p backups && tar -czf backups/config_backup_$(date +%Y%m%d).tar.gz eligibility/config/

# 5. Review error logs
echo "=== Errors This Week ==="
find logs -mtime -7 -exec grep ERROR {} \; | jq '.error_type' | sort | uniq -c | sort -nr
```

### Monthly Maintenance (1 hour)

**First day of month**:

```bash
# 1. Archive old sessions
tar -czf logs/archive_$(date +%Y%m).tar.gz logs/session_*.log.*
find logs -mtime +30 -delete

# 2. Full database integrity check
python -c "
import chromadb
import openpyxl

# Check vector DB
client = chromadb.PersistentClient(path='chroma')
collection = client.get_or_create_collection(name='documents')
count = collection.count()
print(f'✅ Vectors in DB: {count}')

# Check Excel files
for file in ['eligible_customers', 'reasons_file']:
    wb = openpyxl.load_workbook(f'eligibility/data/{file}.xlsx')
    rows = wb.active.max_row - 1
    print(f'✅ {file}: {rows} rows')
"

# 3. Test full flow
python test_rag.py

# 4. Generate capacity report
echo "=== Monthly Capacity Report ===" > reports/$(date +%Y%m)_capacity.txt
du -sh . >> reports/$(date +%Y%m)_capacity.txt
ps aux >> reports/$(date +%Y%m)_capacity.txt

# 5. Review and update documentation
git diff  # Check for code changes
# Update CHANGELOG if needed
```

### Quarterly Maintenance (2 hours)

**Every 3 months**:

- [ ] Security audit (check dependencies)
- [ ] Performance review (analyze logs)
- [ ] Capacity planning (growth trends)
- [ ] Model updates (check Ollama updates)
- [ ] Test disaster recovery

---

## Backup & Recovery

### Backup Strategy

**What to backup**:
- Configuration files (eligibility/config/*.json)
- Data files (eligibility/data/*.xlsx)
- Vector database (chroma/)
- Application logs (logs/)

**What NOT to backup**:
- Virtual environment (venv/) - recreate on restore
- __pycache__ - recreate on restore
- .git history - restore from repo

### Automated Backup

```bash
#!/bin/bash
# backup.sh - Run daily

BACKUP_DIR="backups/$(date +%Y%m%d_%H%M%S)"
mkdir -p "$BACKUP_DIR"

# 1. Backup configs
tar -czf "$BACKUP_DIR/config.tar.gz" eligibility/config/

# 2. Backup data
tar -czf "$BACKUP_DIR/data.tar.gz" eligibility/data/

# 3. Backup vector database
tar -czf "$BACKUP_DIR/chroma.tar.gz" chroma/

# 4. Compress logs (keep last 30 days)
tar -czf "$BACKUP_DIR/logs_$(date +%Y%m).tar.gz" logs/

# 5. Verify all succeeded
if [ -f "$BACKUP_DIR"/*.tar.gz ]; then
    du -sh "$BACKUP_DIR"
    echo "✅ Backup complete: $BACKUP_DIR"
else
    echo "❌ Backup failed"
    exit 1
fi

# 6. Keep only last 10 backups
ls -td backups/*/ | tail -n +11 | xargs -r rm -rf
```

**Schedule backup**:
```bash
# Add to crontab (daily at 2 AM)
0 2 * * * bash /workspaces/organic-fishstick-RAG/backup.sh
```

### Recovery Procedures

#### Full System Recovery

```bash
# 1. Navigate to backup location
cd backups/2024_01_15_023000/

# 2. Stop services
pkill -f streamlit
pkill -f ollama

# 3. Restore configs
tar -xzf config.tar.gz -C /workspaces/organic-fishstick-RAG/

# 4. Restore data
tar -xzf data.tar.gz -C /workspaces/organic-fishstick-RAG/

# 5. Restore database
rm -rf /workspaces/organic-fishstick-RAG/chroma
tar -xzf chroma.tar.gz -C /workspaces/organic-fishstick-RAG/

# 6. Restart services
cd /workspaces/organic-fishstick-RAG
ollama serve &
streamlit run app.py &

# 7. Verify
curl http://localhost:11434/api/tags
```

#### Partial Recovery (Just Data)

```bash
# Restore only Excel files
cd backups/2024_01_15_023000/
tar -xzf data.tar.gz -C /workspaces/organic-fishstick-RAG/
```

#### Partial Recovery (Just Database)

```bash
# Restore vector database without losing new PDFs
cd /workspaces/organic-fishstick-RAG
cp -r chroma chroma.corrupted  # Keep corrupted copy for investigation
cd backups/2024_01_15_023000/
tar -xzf chroma.tar.gz -C /workspaces/organic-fishstick-RAG/
```

---

## Operational Runbooks

### Runbook: Daily Operations

**Time**: 5-10 minutes

```
1. Start day
   └─ Check: Free memory >2GB, disk >1GB
   └─ Start: Ollama (Terminal 1), Streamlit (Terminal 2)
   └─ Verify: Both services responding

2. Monitor operations
   └─ Every 2 hours: Check for errors in logs
   └─ Every 4 hours: Check disk space
   └─ Watch for unusual patterns

3. End day
   └─ Review error log
   └─ Gracefully stop both services
   └─ Verify processes stopped

4. Optional: Compact logs if >500MB
```

### Runbook: Adding New Data

**Time**: 10-30 minutes depending on data size

```
1. Prepare data
   ├─ Excel files: Add accounts to eligibility/data/
   │  └─ eligible_customers.xlsx: ACCOUNTNO, CUSTOMERNAMES
   │  └─ reasons_file.xlsx: account_number, Joint_Check, CLASSIFICATION, ...
   └─ PDFs: Copy to data/ directory

2. Load data
   ├─ Excel: No action needed (auto-loaded on startup)
   └─ PDFs: Run: python populate_database.py

3. Verify
   ├─ Check PDFs indexed: 
   │  python -c "import chromadb; print(chromadb.PersistentClient('chroma').get_or_create_collection('documents').count())"
   └─ Test with query: python query_data.py "sample query"

4. Monitor
   └─ First 10 queries after load: Watch latency
   └─ Check for any new errors in logs
```

### Runbook: Performance Troubleshooting

**Time**: 15-30 minutes

```
1. Identify problem
   ├─ Slow queries? (>5 seconds)
   ├─ High memory? (>4GB)
   ├─ High CPU? (>80%)
   └─ High latency?

2. Investigate
   ├─ Memory: ps aux --sort=-%mem | head -5
   ├─ CPU: top -b | head -20
   ├─ Latency: tail -100 logs/session_*.log | jq '.latency_ms' | statistics
   └─ Network: ping localhost (should be <2ms)

3. Optimize (choose based on problem)
   ├─ If high memory: Reduce k=5→k=3 in query_data.py, restart
   ├─ If slow embeddings: Use nomic-embed-text
   ├─ If slow LLM: Use smaller model or reduce num_predict
   └─ If disk bound: Reduce chunk_size in populate_database.py

4. Verify
   └─ Re-test with same query: Should be faster
   └─ Monitor next 20 queries for consistency
```

### Runbook: Emergency Shutdown

**Time**: 2-3 minutes

```
1. Stop processing
   ├─ Graceful: Ctrl+C in both terminals
   └─ Force: pkill -f streamlit; pkill -f ollama

2. Save state
   ├─ Wait for graceful shutdown to complete
   ├─ Check processes stopped: ps aux | grep -E "streamlit|ollama"
   └─ Optional: Backup recent logs: cp logs/session_*.log logs/backup_emergency/

3. Verify clean shutdown
   ├─ Check ports available: lsof -i :8501; lsof -i :11434
   └─ If ports in use: kill -9 <PID>

4. Document
   └─ Note reason and time in incident log
```

---

## Checklists

### Pre-Deployment Checklist

- [ ] All unit tests pass: `pytest tests/ -v`
- [ ] All integration tests pass: `pytest tests/test_eligibility_integration.py -v`
- [ ] No ERROR in logs: `grep ERROR logs/session_*.log` returns empty
- [ ] Config files valid JSON: `python -m json.tool eligibility/config/*.json`
- [ ] Data files readable: `python -c "import openpyxl; openpyxl.load_workbook('eligibility/data/eligible_customers.xlsx')"`
- [ ] Vector database present: `ls -d chroma/` exists
- [ ] All dependencies installed: `pip list | grep -E "streamlit|langchain|chromadb"`
- [ ] Ollama running with both models: `ollama list | grep -E "nomic|llama"`
- [ ] Streamlit app starts: `timeout 10 streamlit run app.py` (should start without error)
- [ ] No PII in logs: `grep -r "password|ssn|email" logs/` returns empty (optional check)

### Disaster Recovery Checklist

- [ ] Database backup exists: `ls -la backups/*chroma* | wc -l` >0
- [ ] Config backup exists: `ls -la backups/*config* | wc -l` >0
- [ ] Data backup exists: `ls -la backups/*data* | wc -l` >0
- [ ] Backup integrity verified: `tar -tzf backups/latest_backup.tar.gz` succeeds
- [ ] Recovery procedure tested: Did full restore on test machine
- [ ] Recovery RTO acceptable: Can restore in <30 minutes
- [ ] Recovery RPO acceptable: <24 hours of data loss acceptable

### Performance Checklist

- [ ] P50 latency <2 seconds (typical query response)
- [ ] P95 latency <6 seconds (slow query response)
- [ ] P99 latency <10 seconds (very slow edge case)
- [ ] Error rate <1%: `(error_count / total_requests) * 100 < 1`
- [ ] Memory usage <4GB: `free -h | grep Mem` shows <4GB used
- [ ] CPU usage <80%: `top` shows app using <80% CPU
- [ ] Disk I/O healthy: `iostat -x` shows wait% <10%
- [ ] Network latency <2ms: `ping localhost` shows <2ms

### Incident Response Checklist

- [ ] Incident severity assessed: HIGH/MEDIUM/LOW
- [ ] Users/impact quantified: X users affected, Y services down
- [ ] Incident ID created: INC-2024-XXX
- [ ] Root cause identified: Why it happened
- [ ] Remediation implemented: How it was fixed
- [ ] System verified working: All tests pass, queries succeed
- [ ] Preventive measures identified: How to avoid recurrence
- [ ] Incident log updated: Complete record for analysis
- [ ] Stakeholders notified: Users informed of resolution
- [ ] Post-incident review scheduled: Analysis meeting within 48h

---

## Contact & Escalation

### Support Channels

| Level | Contact | Response Time |
|-------|---------|----------------|
| L1 - Minor issue | Check logs, run health_check.sh | 15 min |
| L2 - Degraded service | Follow troubleshooting guide | 1 hour |
| L3 - Critical outage | Execute incident response | 15 min |

### Escalation Path

```
User Reports Issue
  ↓
Check status (1 min) → If operational, reply "working as designed"
  ↓
Review logs (5 min) → If clear error, apply fix
  ↓
Escalate to Level 2 (30 min) → Follow troubleshooting by scenario
  ↓
Escalate to Level 3 (60 min) → Incident response + engineering review
```

---

**For setup help, see**: [SETUP_GUIDE.md](SETUP_GUIDE.md)  
**For architecture details, see**: [SYSTEM_ARCHITECTURE.md](SYSTEM_ARCHITECTURE.md)

---

*Last Updated: 2024*  
*Owner: System Admin*  
*Review Frequency: Quarterly*
