import { StruggleTracker } from '../struggleTracker';

describe('StruggleTracker', () => {
  let tracker: StruggleTracker;
  const FILE_A = '/workspace/app.py';
  const FILE_B = '/workspace/utils.py';

  beforeEach(() => {
    tracker = new StruggleTracker();
  });

  // ── Threshold behaviour ──────────────────────────────────────────────────

  test('returns false for the first 4 saves within the window', () => {
    const now = Date.now();
    for (let i = 0; i < 4; i++) {
      expect(tracker.recordSave(FILE_A, now + i * 1000)).toBe(false);
    }
  });

  test('returns true on exactly the 5th save within the window', () => {
    const now = Date.now();
    for (let i = 0; i < 4; i++) {
      tracker.recordSave(FILE_A, now + i * 1000);
    }
    expect(tracker.recordSave(FILE_A, now + 4000)).toBe(true);
  });

  test('returns true on saves beyond the 5th within the window', () => {
    const now = Date.now();
    for (let i = 0; i < 6; i++) {
      tracker.recordSave(FILE_A, now + i * 1000);
    }
    // 6th save should also return true
    expect(tracker.recordSave(FILE_A, now + 6000)).toBe(true);
  });

  // ── Window pruning ───────────────────────────────────────────────────────

  test('saves outside the 10-minute window are not counted', () => {
    const now = Date.now();
    const elevenMinutesAgo = now - 11 * 60 * 1000;

    // Record 4 saves 11 minutes ago (outside window)
    for (let i = 0; i < 4; i++) {
      tracker.recordSave(FILE_A, elevenMinutesAgo + i * 1000);
    }

    // Now record 1 save within the window — should NOT trigger (only 1 in window)
    expect(tracker.recordSave(FILE_A, now)).toBe(false);
  });

  test('recentSaveCount returns only saves within the window', () => {
    const now = Date.now();
    const elevenMinutesAgo = now - 11 * 60 * 1000;

    tracker.recordSave(FILE_A, elevenMinutesAgo);  // outside window
    tracker.recordSave(FILE_A, now - 5 * 60 * 1000);  // inside window
    tracker.recordSave(FILE_A, now - 1 * 60 * 1000);  // inside window

    expect(tracker.recentSaveCount(FILE_A, now)).toBe(2);
  });

  // ── Reset behaviour ──────────────────────────────────────────────────────

  test('reset clears history so subsequent saves start fresh', () => {
    const now = Date.now();
    // Trigger the warning
    for (let i = 0; i < 5; i++) {
      tracker.recordSave(FILE_A, now + i * 1000);
    }
    tracker.reset(FILE_A);

    // After reset, 4 more saves should not trigger
    for (let i = 0; i < 4; i++) {
      expect(tracker.recordSave(FILE_A, now + 10000 + i * 1000)).toBe(false);
    }
  });

  test('reset followed by 5 new saves triggers again', () => {
    const now = Date.now();
    for (let i = 0; i < 5; i++) {
      tracker.recordSave(FILE_A, now + i * 1000);
    }
    tracker.reset(FILE_A);

    for (let i = 0; i < 4; i++) {
      tracker.recordSave(FILE_A, now + 10000 + i * 1000);
    }
    expect(tracker.recordSave(FILE_A, now + 14000)).toBe(true);
  });

  // ── Per-file isolation ───────────────────────────────────────────────────

  test('saves to FILE_A do not affect FILE_B count', () => {
    const now = Date.now();
    for (let i = 0; i < 10; i++) {
      tracker.recordSave(FILE_A, now + i * 1000);
    }
    expect(tracker.recentSaveCount(FILE_B, now + 10000)).toBe(0);
  });

  test('FILE_A and FILE_B track independently', () => {
    const now = Date.now();
    // 5 saves on FILE_A
    for (let i = 0; i < 5; i++) {
      tracker.recordSave(FILE_A, now + i * 1000);
    }
    // Only 2 saves on FILE_B
    tracker.recordSave(FILE_B, now);
    tracker.recordSave(FILE_B, now + 1000);

    expect(tracker.recentSaveCount(FILE_A, now + 5000)).toBe(5);
    expect(tracker.recentSaveCount(FILE_B, now + 5000)).toBe(2);
  });

  // ── recentSaveCount ──────────────────────────────────────────────────────

  test('recentSaveCount returns 0 for a file with no saves', () => {
    expect(tracker.recentSaveCount('/no/saves/here.py')).toBe(0);
  });

  test('recentSaveCount returns 0 after reset', () => {
    const now = Date.now();
    for (let i = 0; i < 3; i++) {
      tracker.recordSave(FILE_A, now + i * 1000);
    }
    tracker.reset(FILE_A);
    expect(tracker.recentSaveCount(FILE_A, now + 5000)).toBe(0);
  });
});
