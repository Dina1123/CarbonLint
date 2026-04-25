"use strict";
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
var __createBinding = (this && this.__createBinding) || (Object.create ? (function(o, m, k, k2) {
    if (k2 === undefined) k2 = k;
    var desc = Object.getOwnPropertyDescriptor(m, k);
    if (!desc || ("get" in desc ? !m.__esModule : desc.writable || desc.configurable)) {
      desc = { enumerable: true, get: function() { return m[k]; } };
    }
    Object.defineProperty(o, k2, desc);
}) : (function(o, m, k, k2) {
    if (k2 === undefined) k2 = k;
    o[k2] = m[k];
}));
var __setModuleDefault = (this && this.__setModuleDefault) || (Object.create ? (function(o, v) {
    Object.defineProperty(o, "default", { enumerable: true, value: v });
}) : function(o, v) {
    o["default"] = v;
});
var __importStar = (this && this.__importStar) || (function () {
    var ownKeys = function(o) {
        ownKeys = Object.getOwnPropertyNames || function (o) {
            var ar = [];
            for (var k in o) if (Object.prototype.hasOwnProperty.call(o, k)) ar[ar.length] = k;
            return ar;
        };
        return ownKeys(o);
    };
    return function (mod) {
        if (mod && mod.__esModule) return mod;
        var result = {};
        if (mod != null) for (var k = ownKeys(mod), i = 0; i < k.length; i++) if (k[i] !== "default") __createBinding(result, mod, k[i]);
        __setModuleDefault(result, mod);
        return result;
    };
})();
Object.defineProperty(exports, "__esModule", { value: true });
const path = __importStar(require("path"));
const bridge_1 = require("../bridge");
// Resolve the backend server path relative to this test file:
// carbon-optimizer-extension/src/__tests__/ -> ../../.. -> workspace root -> kiro-carbon-optimizer/
const BACKEND_PATH = path.resolve(__dirname, '..', '..', '..', 'kiro-carbon-optimizer', 'backend_server.py');
// Use 'python' on Windows as fallback
const PYTHON = process.platform === 'win32' ? 'python' : 'python3';
describe('Bridge integration (real Python backend)', () => {
    let bridge;
    beforeAll(async () => {
        bridge = new bridge_1.Bridge(PYTHON, BACKEND_PATH);
        await bridge.start();
        // Give the backend a moment to initialise
        await new Promise((resolve) => setTimeout(resolve, 500));
    }, 15000);
    afterAll(() => {
        bridge.dispose();
    });
    test('analyze_efficiency returns a result with an issues array', async () => {
        const result = await bridge.call('analyze_efficiency', { code: 'x = [i for i in range(1000)]' });
        expect(result).toHaveProperty('issues');
        expect(Array.isArray(result.issues)).toBe(true);
        expect(result).toHaveProperty('functions');
    }, 15000);
    test('analyze_efficiency detects nested loop issue', async () => {
        const code = 'for i in range(10):\n    for j in range(10):\n        pass';
        const result = await bridge.call('analyze_efficiency', { code });
        const nestedLoopIssue = result.issues.find((i) => i.issue_id.startsWith('nested-loop'));
        expect(nestedLoopIssue).toBeDefined();
    }, 15000);
    test('analyze_efficiency returns error for empty code', async () => {
        await expect(bridge.call('analyze_efficiency', { code: '' })).rejects.toThrow();
    }, 15000);
    test('analyze_configs returns an array for a non-existent path', async () => {
        const result = await bridge.call('analyze_configs', {
            workspace_root: '/nonexistent/path/that/does/not/exist'
        });
        expect(Array.isArray(result)).toBe(true);
        expect(result).toHaveLength(0);
    }, 15000);
});
//# sourceMappingURL=integration.test.js.map