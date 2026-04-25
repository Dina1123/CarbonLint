/**
 * Integration test: verifies a full round-trip with the real Python backend.
 *
 * Prerequisites:
 *   - Python 3 must be installed and accessible as 'python3' (or 'python' on Windows)
 *   - kiro-carbon-optimizer dependencies must be installed:
 *       pip install -r kiro-carbon-optimizer/requirements.txt
 *
 * Run from carbon-optimizer-extension/:
 *   npx jest src/__tests__/integration.test.ts --testTimeout=30000
 */

import * as path from 'path';
import { Bridge } from '../bridge';

// Resolve the backend server path relative to this test file:
// carbon-optimizer-extension/src/__tests__/ -> ../../.. -> workspace root -> kiro-carbon-optimizer/
const BACKEND_PATH = path.resolve(
  __dirname,
  '..', '..', '..', 'kiro-carbon-optimizer', 'backend_server.py'
);

// Use 'python' on Windows as fallback
const PYTHON = process.platform === 'win32' ? 'python' : 'python3';

describe('Bridge integration (real Python backend)', () => {
  let bridge: Bridge;

  beforeAll(async () => {
    bridge = new Bridge(PYTHON, BACKEND_PATH);
    await bridge.start();
    // Give the backend a moment to initialise
    await new Promise((resolve) => setTimeout(resolve, 500));
  }, 15000);

  afterAll(() => {
    bridge.dispose();
  });

  test('analyze_efficiency returns a result with an issues array', async () => {
    const result = await bridge.call<{ issues: unknown[]; functions: unknown[] }>(
      'analyze_efficiency',
      { code: 'x = [i for i in range(1000)]' }
    );
    expect(result).toHaveProperty('issues');
    expect(Array.isArray(result.issues)).toBe(true);
    expect(result).toHaveProperty('functions');
  }, 15000);

  test('analyze_efficiency detects nested loop issue', async () => {
    const code = 'for i in range(10):\n    for j in range(10):\n        pass';
    const result = await bridge.call<{ issues: Array<{ issue_id: string }> }>(
      'analyze_efficiency',
      { code }
    );
    const nestedLoopIssue = result.issues.find((i) => i.issue_id.startsWith('nested-loop'));
    expect(nestedLoopIssue).toBeDefined();
  }, 15000);

  test('analyze_efficiency returns error for empty code', async () => {
    await expect(
      bridge.call('analyze_efficiency', { code: '' })
    ).rejects.toThrow();
  }, 15000);

  test('analyze_configs returns an array for a non-existent path', async () => {
    const result = await bridge.call<unknown[]>('analyze_configs', {
      workspace_root: '/nonexistent/path/that/does/not/exist'
    });
    expect(Array.isArray(result)).toBe(true);
    expect(result).toHaveLength(0);
  }, 15000);
});
