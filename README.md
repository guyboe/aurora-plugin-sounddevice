# Install with dependencies

```bash
pip install --extra-index-url https://test.pypi.org/simple/ -e .
```

# Create config (example)

```yaml
queues:
  url: amqp://guest:guest@localhost
  exchanges:
    detect:
      name: aurora.detect
      type: fanout
      proxy: proxy/aurora.detect
    play:
      name: aurora.play
      type: fanout
      proxy: proxy/aurora.play
    execute:
      name: aurora.execute
      type: fanout
      proxy: proxy/aurora.execute
  queues:
    - name: aurora.play
      exchange: play
      callback: _play

output:
  samplerate: 24000
```

# Validate config

```bash
python -m commands aurora_plugin_sounddevice config
```

# List all available commands

```bash
python -m commands aurora_plugin_sounddevice --help
```

# Run listen and consume in separate consoles

```bash
python -m commands aurora_plugin_sounddevice listen

python -m commands aurora_plugin_sounddevice consume
```
