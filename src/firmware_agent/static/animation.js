/**
 * Shared animation module for PS3 Firmware Agent.
 * Drives SVG trace pulses and LED state using a strictly controlled requestAnimationFrame loop
 * based on real execution timestamps (t_ns).
 */

export class CircuitAnimator {
    constructor(svgContext, options = {}) {
        this.svg = svgContext;
        this.pulseDot = this.svg.querySelector('.trace-pulse');
        this.path = this.svg.querySelector('.trace-line');
        this.leds = Array.from(this.svg.querySelectorAll('.led-indicator'));
        this.rafId = null;
        this.traceData = null;
        this.isPlaying = false;
        
        // Options
        this.loopDurationMs = options.loopDurationMs || 4000;
        this.pathLen = this.path ? this.path.getTotalLength() : 0;
    }

    /**
     * Load new trace data.
     */
    loadTrace(traceData) {
        this.traceData = traceData;
        this.stop(); // Reset animation
    }

    /**
     * Start the animation loop.
     */
    start() {
        if (!this.traceData || !this.traceData.channels?.gpio?.length) {
            console.warn("No GPIO trace data available. Animation stays idle.");
            return;
        }
        
        if (this.isPlaying) return;
        this.isPlaying = true;
        this.startTime = null;
        this.rafId = requestAnimationFrame(this.step.bind(this));
        
        // Show pulse
        if (this.pulseDot) {
            this.pulseDot.setAttribute('opacity', '1');
        }
    }

    /**
     * Stop and completely halt the RAF loop.
     */
    stop() {
        this.isPlaying = false;
        if (this.rafId) {
            cancelAnimationFrame(this.rafId);
            this.rafId = null;
        }
        // Hide pulse and reset LEDs
        if (this.pulseDot) {
            this.pulseDot.setAttribute('opacity', '0');
        }
        this.leds.forEach(led => led.className.baseVal = 'led-indicator led-off');
    }

    /**
     * The RAF callback.
     */
    step(timestamp) {
        if (!this.isPlaying) return; // Failsafe
        
        if (!this.startTime) this.startTime = timestamp;
        const elapsed = (timestamp - this.startTime) % this.loopDurationMs;
        const pct = elapsed / this.loopDurationMs;
        
        // 1. Move the pulse dot along the path
        if (this.pulseDot && this.path) {
            const pt = this.path.getPointAtLength(pct * this.pathLen);
            this.pulseDot.setAttribute('cx', pt.x);
            this.pulseDot.setAttribute('cy', pt.y);
        }
        
        // 2. Synchronize LEDs based on trace t_ns data
        const durationNs = this.traceData.duration_ns || 1;
        const currentSimNs = pct * durationNs;
        
        // Very basic sync: just light up LEDs if we pass their first high transition
        // In a more complex board designer, we'd map specific pins to specific LEDs.
        const gpio = this.traceData.channels.gpio;
        const firstHigh = gpio.find(g => g.value === 1);
        const firstHighNs = firstHigh ? firstHigh.t_ns : Infinity;
        
        this.leds.forEach((led, idx) => {
            // Stagger the LED activation slightly for effect based on their index
            const triggerNs = firstHighNs * (0.5 + (idx * 0.5));
            if (currentSimNs >= triggerNs) {
                led.className.baseVal = 'led-indicator led-on';
            } else {
                led.className.baseVal = 'led-indicator led-off';
            }
        });
        
        this.rafId = requestAnimationFrame(this.step.bind(this));
    }
}
