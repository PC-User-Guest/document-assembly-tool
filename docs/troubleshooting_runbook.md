# Troubleshooting Runbook

This guide addresses common issues and provides resolution steps for the Document Assembly Tool.

## Common Issues

### 1. Placeholders Not Replaced

**Symptoms:**
- Template output still contains `{{field_name}}` instead of data
- No errors in logs

**Diagnostic Steps:**

```bash
# Enable debug logging to see which placeholders are found
python -m src.document_assembler -d data.docx -t template.docx -o output.docx --log-level DEBUG
```

**Common Causes & Solutions:**

| Cause | Solution |
|-------|----------|
| **Field name mismatch** | Verify field names in data source exactly match placeholder names (case-sensitive). Use `--log-level DEBUG` to see discovered fields. |
| **Placeholder in wrong format** | Default pattern is `{{field}}`. If using inline formatting, ensure placeholder is in its own run. Use `--placeholder-pattern` if custom syntax needed. |
| **Template encoding issues** | Re-save template in UTF-8 encoding. Some Word versions may use different codepages. |
| **Multi-paragraph placeholders** | If placeholder spans multiple runs, try using entire paragraph method. |

**Debug Example:**

```python
from docx import Document

# Inspect template structure
doc = Document('template.docx')
for p in doc.paragraphs:
    print(f"Paragraph: {p.text}")
    for r in p.runs:
        print(f"  Run: {r.text}")
```

---

### 2. Style Mismatch Warnings

**Symptoms:**
```
WARNING - Style 'Heading 3' not found; using default.
```

**Cause:** Data source references a style that doesn't exist in the template.

**Solutions:**

1. **Add missing style to template:**
   - Open template in Word
   - Go to Styles panel
   - Create missing style with same name as in data

2. **Use available styles in data:**
   - Inspect template styles: `python scripts/list_styles.py template.docx`
   - Update data source to use only available styles

3. **Accept default styling:**
   - Warning is non-fatal; document will still be generated
   - Formatting will use template's default style

---

### 3. Encryption Key Problems

**Symptoms:**
```
ERROR - No such file or directory: ~/.docassembler/encryption.key
ERROR - Failed to decrypt output document
```

**Causes & Solutions:**

| Issue | Solution |
|-------|----------|
| **Key file missing** | Key is auto-generated on first use. If deleted, regenerate: `python scripts/generate_key.py` |
| **Key file corrupted** | Delete corrupted key and regenerate: `rm ~/.docassembler/encryption.key` then re-run tool |
| **Wrong key for decryption** | Encrypted documents can only be decrypted with the same key. Ensure correct key is loaded. |
| **Permissions denied** | Check key file permissions (`ls -la ~/.docassembler/encryption.key`). Should be `600` (owner only). Fix: `chmod 600 ~/.docassembler/encryption.key` |

**Backup & Recovery:**

```bash
# Backup key to secure location
cp ~/.docassembler/encryption.key /secure/location/backup_key

# Restore from backup
cp /secure/location/backup_key ~/.docassembler/encryption.key
chmod 600 ~/.docassembler/encryption.key
```

---

### 4. Permission Denied Errors

**Symptoms:**
```
ERROR - Permission denied: /path/to/output.docx
ERROR - Permission denied when reading data.docx
```

**Causes & Solutions:**

| Cause | Solution |
|-------|----------|
| **Output directory not writable** | Verify output directory exists and has write permissions: `mkdir -p /path && chmod 755 /path` |
| **Input file read-only** | Remove read-only flag: `chmod u+w data.docx` |
| **File in use (Windows)** | Close file in Word/Excel before running tool |
| **SELinux or AppArmor** (Linux) | Check security policy: `getenforce` (SELinux) or `aa-status` (AppArmor) |

---

### 5. Out of Memory Errors

**Symptoms:**
```
MemoryError: Unable to allocate X bytes
ProcessPoolExecutor: Worker process died unexpectedly
```

**Causes & Solutions:**

| Cause | Solution |
|-------|----------|
| **Too many concurrent workers** | Reduce `--concurrency` parameter. Default is CPU count; try `--concurrency 2` or `4`. |
| **Large template or data** | Split large documents into smaller batches. |
| **Memory leak in template cache** | Clear cache: `rm document_assembly.db` and restart. |
| **System out of memory** | Monitor with `top` or `htop`. Free up resources before retry. |

**Memory Profiling:**

```bash
# Profile memory usage
python -m memory_profiler examples/enterprise_integration.py
```

---

### 6. Database Locked Errors

**Symptoms:**
```
sqlite3.OperationalError: database is locked
WARNING - Retrying operation after lock timeout
```

**Causes & Solutions:**

| Cause | Solution |
|-------|----------|
| **Multiple processes writing simultaneously** | Enable WAL mode (auto-enabled in v2.0+) for concurrent writes. |
| **Long-running transaction** | Reduce transaction scope. Break into smaller batches. |
| **Network storage contention** | Use local SQLite DB, not NFS. If must use NFS, enable WAL: `PRAGMA journal_mode=WAL;` |
| **Stale lock file** | Remove lock files: `rm ~/.docassembler/*.db-shm ~/.docassembler/*.db-wal` |

**WAL Verification:**

```bash
sqlite3 document_assembly.db "PRAGMA journal_mode;"
# Output should be: journal_mode|wal
```

---

### 7. CSV Parsing Errors

**Symptoms:**
```
ERROR - CSV parsing failed: field size exceeds limit (1048576)
```

**Causes & Solutions:**

| Cause | Solution |
|-------|----------|
| **CSV field too large** | Increase field size limit in `src/document_assembler.py`: `csv.field_size_limit(2**20)` |
| **Wrong delimiter** | CSV assumes comma (`,`). If using tabs/semicolons, convert or specify in tool (future feature). |
| **Encoding mismatch** | Save CSV as UTF-8. Use tool to detect: `file -i data.csv` |

**Convert to UTF-8:**

```bash
# On macOS/Linux
iconv -f ISO-8859-1 -t UTF-8 data.csv > data_utf8.csv

# On Windows (PowerShell)
Get-Content data.csv -Encoding Default | Out-File data_utf8.csv -Encoding UTF8
```

---

### 8. Performance Degradation

**Symptoms:**
- Processing time grows with each document
- Memory usage increases over time
- CPU usage stays high even when idle

**Causes & Solutions:**

| Cause | Solution |
|-------|----------|
| **Cache growing unbounded** | Set cache size limit. Default: 500MB. Clear periodically: `python -c "from src.advanced_features import persistence; persistence.db.execute('DELETE FROM templates WHERE created_at < datetime(now, \\'-30 days\\')')"` |
| **Log file too large** | Rotate logs: use `logging.handlers.RotatingFileHandler` |
| **Audit trail accumulation** | Archive old audit records: `sqlite3 document_assembly.db "DELETE FROM processing_history WHERE created_at < datetime(now, '-90 days')"` |
| **Process leak** | Monitor processes: `ps aux | grep python` |

**Performance Metrics:**

```bash
# Get current metrics from health check
curl http://localhost:8000/health | jq .

# Expected throughput (single-threaded):
# 4.27 docs/sec baseline
# 8.93 docs/sec with --concurrency 4 (2.09x)
# 7.45 docs/sec with multiprocessing (1.74x)
```

---

### 9. Placeholder Pattern Issues

**Symptoms:**
```
ERROR - Invalid regular expression: (unbalanced parenthesis)
```

**Causes & Solutions:**

| Cause | Solution |
|-------|----------|
| **Invalid regex syntax** | Test pattern with Python: `import re; re.compile(r'your_pattern')` |
| **Missing named group** | Pattern must include `(?P<field_name>...)`. Example: `r'<<(?P<field_name>\w+)>>'` |
| **Escape sequences** | Remember to use raw strings (`r''`). Backslashes need escaping: `r'\{'` not `'\'`. |

**Test Pattern:**

```bash
python << 'EOF'
import re
pattern = r'<<\s*(?P<field_name>\w+)\s*>>'
test_text = "This is << my_field >> here"
matches = re.findall(pattern, test_text)
print(f"Matches: {matches}")
EOF
```

---

### 10. Health Check Failures

**Symptoms:**
```
curl http://localhost:8000/health
curl: (7) Failed to connect to port 8000: Connection refused

GET /health returns 503 Service Unavailable
```

**Causes & Solutions:**

| Cause | Solution |
|-------|----------|
| **Server not started** | Enable observability: `--enable-observability` or call `start_health_check_server()` in code. |
| **Port already in use** | Change port: `python -c "from src.advanced_features import start_health_check_server; start_health_check_server(8001)"` |
| **Database connection failed** | Check DB connectivity: `sqlite3 document_assembly.db "SELECT 1;"` |
| **Firewall blocking** | Verify firewall rules: `sudo iptables -L \| grep 8000` (Linux) |

**Debug Health Status:**

```bash
# Verbose health check with timing
time curl -v http://localhost:8000/health 2>&1 | grep -E "(HTTP|uptime|status|reason)"
```

---

## Monitoring & Alerts

### Prometheus Metrics to Monitor

```promql
# Alert if error rate is high
rate(errors_total[5m]) > 0.1

# Alert if processing time is slow
histogram_quantile(0.95, processing_seconds) > 5

# Alert if cache performance degrades
cache_hit_rate < 0.5

# Alert if active workers are stuck
active_workers > 4 for 10m
```

### Health Check Response Codes

| Code | Meaning | Action |
|------|---------|--------|
| **200 OK** | All systems healthy | Continue normal operation |
| **503 Service Unavailable** | Database or critical component failed | Check reason field; restart if necessary |

### Accessing Audit Logs

```bash
# View recent processing history
sqlite3 document_assembly.db "SELECT template_name, status, processing_time FROM processing_history ORDER BY created_at DESC LIMIT 10;"

# Find failed processing
sqlite3 document_assembly.db "SELECT * FROM processing_history WHERE status='failed';"

# Verify audit integrity (check hashes)
sqlite3 document_assembly.db "SELECT output_path, output_hash FROM processing_history WHERE created_at > datetime(now, '-1 day');"
```

---

## Emergency Recovery

### Corrupted Database

```bash
# Backup current DB
cp document_assembly.db document_assembly.db.bak

# Rebuild DB from scratch
rm document_assembly.db
python -c "from src.advanced_features import persistence; persistence._init_db()"

# Restore from backup if needed
cp document_assembly.db.bak document_assembly.db
```

### Worker Process Stuck

```bash
# Find stuck Python processes
ps aux | grep python | grep document_assembler

# Kill gracefully (SIGTERM)
kill -15 <pid>

# Force kill if necessary (SIGKILL)
kill -9 <pid>
```

### Clear Cache

```bash
# Remove template cache entirely
sqlite3 document_assembly.db "DELETE FROM templates; VACUUM;"

# Remove audit history
sqlite3 document_assembly.db "DELETE FROM processing_history WHERE created_at < datetime(now, '-30 days'); VACUUM;"
```

---

## Getting Help

1. **Check logs:** `--log-level DEBUG` gives detailed execution trace
2. **Run health check:** `curl http://localhost:8000/health` to check system status
3. **Inspect metrics:** Export Prometheus metrics to understand performance
4. **Review audit trail:** Query SQLite audit DB to trace document processing steps
5. **Run benchmarks:** `python scripts/benchmark_scaling.py` to verify performance baseline

For issues not covered here, enable profiling and collect diagnostics:

```bash
python -c "from src.advanced_features import profiling_context; exec(open('your_script.py').read())" 
# Generates profile.prof for analysis
```
