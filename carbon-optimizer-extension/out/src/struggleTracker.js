"use strict";
Object.defineProperty(exports, "__esModule", { value: true });
exports.StruggleTracker = void 0;
/**
 * StruggleTracker — tracks per-file save frequency and detects AI retry loops.
 *
 * Fires a warning when a file has been saved THRESHOLD or more times
 * within a sliding WINDOW_MS millisecond window.
 */
class StruggleTracker {
    constructor() {
        /** Sliding window duration in milliseconds (10 minutes). */
        this.WINDOW_MS = 10 * 60 * 1000;
        /** Number of saves within the window that triggers a warning. */
        this.THRESHOLD = 5;
        /** Map from file path to array of save timestamps (ms since epoch). */
        this.saveHistory = new Map();
    }
    /**
     * Record a save event for the given file path.
     * Prunes timestamps outside the sliding window, then checks the threshold.
     *
     * @returns true if the save count within the window has reached THRESHOLD,
     *          false otherwise.
     */
    recordSave(filePath, nowMs = Date.now()) {
        const history = this.saveHistory.get(filePath) ?? [];
        const windowStart = nowMs - this.WINDOW_MS;
        // Prune old entries
        const pruned = history.filter((t) => t >= windowStart);
        pruned.push(nowMs);
        this.saveHistory.set(filePath, pruned);
        return pruned.length >= this.THRESHOLD;
    }
    /**
     * Reset the save history for a file.
     * Called after a struggle warning has been shown so the next saves
     * start a fresh window.
     */
    reset(filePath) {
        this.saveHistory.set(filePath, []);
    }
    /**
     * Return the count of saves within the sliding window for a file.
     * Useful for testing and for the extension to read the current count.
     */
    recentSaveCount(filePath, nowMs = Date.now()) {
        const history = this.saveHistory.get(filePath) ?? [];
        const windowStart = nowMs - this.WINDOW_MS;
        return history.filter((t) => t >= windowStart).length;
    }
}
exports.StruggleTracker = StruggleTracker;
//# sourceMappingURL=struggleTracker.js.map