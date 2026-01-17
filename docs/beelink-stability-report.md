# Beelink AI Brain Stability Report

## Current Configuration (STABLE)
```
Model: Ministral-3-14B-Reasoning-2512-Q4_K_M.gguf (7.7GB)
Memory Usage: 907MB / 24GB RAM (3.8%)
GPU: AMD Radeon 680M (Vulkan backend)
GPU Layers: 99 (all offloaded)
CPU Threads: 2
Context Window: 2048 tokens
Power Draw: 3-4W idle, ~8W during inference
Temperature: 38°C idle, 48°C peak during inference
```

## Crash Analysis (Historical)
**Symptom:** System crashed during inference before scaling down
**Root Cause:** Likely one or more of:
1. **Power surge** - Larger model + more threads caused PSU overload
2. **Memory pressure** - Larger quantization (Q5/Q6) used more RAM
3. **Thermal throttling** - More CPU/GPU load generated heat
4. **OOM (Out of Memory)** - System ran out of RAM

## Current Stability Measures ✅
1. **Q4 quantization** - Reduced model size from potential 10-15GB to 7.7GB
2. **2 threads only** - Minimized CPU power draw
3. **GPU offloading** - Reduced CPU load significantly  
4. **2048 context** - Conservative context window
5. **Power monitoring** - Active logging at ~/llm-power-monitor.log

## Performance Characteristics
- **Response Time:** 25-60 seconds per query
- **Temperature Rise:** +9-10°C during inference (acceptable)
- **Memory Footprint:** Very stable at ~900MB
- **Uptime:** 10+ hours with no crashes

## Optimization Options (Without Risking Stability)

### Option 1: Slightly Faster (Low Risk)
```bash
# Increase threads from 2 to 4
-t 4  # Uses more CPU but still conservative
```
**Pros:** ~20-30% faster responses
**Cons:** +2-3W power draw, +5°C temperature
**Risk:** Low (still well within thermal limits)

### Option 2: Much Faster (Medium Risk)
```bash
# Switch to Q3 quantization
# Download smaller model: Ministral-3-14B-Q3_K_M.gguf (~5.5GB)
```
**Pros:** 40-50% faster inference, less RAM usage
**Cons:** Slightly lower quality responses
**Risk:** Medium (less stable than Q4, but should work)

### Option 3: Balanced (Recommended)
```bash
# Keep Q4, increase threads to 3, reduce context
-t 3 -c 1536
```
**Pros:** 15-20% faster, more stable than 4 threads
**Cons:** Shorter conversation memory
**Risk:** Very Low

### Option 4: Maximum Safety (Current)
```bash
# Keep everything as-is
-t 2 -c 2048 -ngl 99
```
**Pros:** Proven stable, no crashes
**Cons:** Slower responses (25-60s)
**Risk:** None

## Monitoring & Prevention
**Active Monitoring:** ~/llm-power-monitor.log (logs every 3 seconds)
- CPU temperature
- GPU temperature and power
- LLM process status
- System load

**Check commands:**
```bash
# Live monitoring
ssh brain_ai@192.168.68.51 'tail -f ~/llm-power-monitor.log'

# Health check
ssh brain_ai@192.168.68.51 '~/check-llm-health.sh'

# View before crash
ssh brain_ai@192.168.68.51 'tail -100 ~/llm-power-monitor.log'
```

## Recommendations
1. **Keep current setup** - It's working, stable, and safe
2. **Monitor for 1 week** - Collect baseline data
3. **If no crashes** - Consider Option 3 (3 threads, 1536 context)
4. **If crashes occur** - Check logs immediately for patterns
5. **Never exceed** - 4 threads or 2048 context without testing

## Power Supply Considerations
The Beelink's fragile power supply benefits from:
- ✅ Conservative thread count (reduces power spikes)
- ✅ GPU offloading (spreads load between CPU/GPU)
- ✅ Q4 quantization (smaller memory footprint)
- ⚠️ Avoid sudden power draws (don't run other heavy tasks during inference)

## Future Options
- **Better PSU** - Upgrade power supply for more headroom
- **Smaller model** - Try Llama 3.1 8B for faster responses
- **ROCm backend** - May be more efficient than Vulkan (requires testing)
- **Disable video output in BIOS** - Save 5-10W if not needed
