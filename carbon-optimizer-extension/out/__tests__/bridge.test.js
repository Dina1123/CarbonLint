"use strict";
Object.defineProperty(exports, "__esModule", { value: true });
const bridge_1 = require("../bridge");
const events_1 = require("events");
// Mock child_process.spawn
jest.mock('child_process', () => ({
    spawn: jest.fn(),
}));
const child_process_1 = require("child_process");
function makeMockProcess() {
    const stdout = new events_1.EventEmitter();
    const stderr = new events_1.EventEmitter();
    const stdin = { write: jest.fn((data, cb) => { cb && cb(); }) };
    const proc = new events_1.EventEmitter();
    proc.stdout = stdout;
    proc.stderr = stderr;
    proc.stdin = stdin;
    proc.killed = false;
    proc.kill = jest.fn(() => { proc.killed = true; });
    return proc;
}
describe('Bridge', () => {
    let mockProc;
    beforeEach(() => {
        jest.clearAllMocks();
        mockProc = makeMockProcess();
        child_process_1.spawn.mockReturnValue(mockProc);
    });
    test('start() spawns the backend process with correct args', async () => {
        const bridge = new bridge_1.Bridge('python3', '/path/to/backend_server.py');
        await bridge.start();
        expect(child_process_1.spawn).toHaveBeenCalledWith('python3', ['/path/to/backend_server.py'], expect.any(Object));
        bridge.dispose();
    });
    test('call() serializes request as newline-delimited JSON', async () => {
        const bridge = new bridge_1.Bridge('python3', '/path/to/backend_server.py');
        await bridge.start();
        const promise = bridge.call('analyze_efficiency', { code: 'x = 1' });
        // Verify stdin.write was called with valid JSON ending in \n
        expect(mockProc.stdin.write).toHaveBeenCalledTimes(1);
        const written = mockProc.stdin.write.mock.calls[0][0];
        expect(written.endsWith('\n')).toBe(true);
        const parsed = JSON.parse(written.trim());
        expect(parsed.method).toBe('analyze_efficiency');
        expect(parsed.params).toEqual({ code: 'x = 1' });
        expect(typeof parsed.id).toBe('string');
        // Simulate response
        const response = JSON.stringify({ id: parsed.id, result: { functions: [], issues: [] } }) + '\n';
        mockProc.stdout.emit('data', Buffer.from(response));
        const result = await promise;
        expect(result).toEqual({ functions: [], issues: [] });
        bridge.dispose();
    });
    test('call() resolves with correct result matching request ID', async () => {
        const bridge = new bridge_1.Bridge('python3', '/path/to/backend_server.py');
        await bridge.start();
        const promise = bridge.call('analyze_efficiency', { code: 'x = 1' });
        const written = mockProc.stdin.write.mock.calls[0][0];
        const { id } = JSON.parse(written.trim());
        mockProc.stdout.emit('data', Buffer.from(JSON.stringify({ id, result: { issues: [] } }) + '\n'));
        const result = await promise;
        expect(result.issues).toEqual([]);
        bridge.dispose();
    });
    test('concurrent calls each resolve independently', async () => {
        const bridge = new bridge_1.Bridge('python3', '/path/to/backend_server.py');
        await bridge.start();
        const p1 = bridge.call('method1', {});
        const p2 = bridge.call('method2', {});
        const id1 = JSON.parse(mockProc.stdin.write.mock.calls[0][0].trim()).id;
        const id2 = JSON.parse(mockProc.stdin.write.mock.calls[1][0].trim()).id;
        // Respond in reverse order
        mockProc.stdout.emit('data', Buffer.from(JSON.stringify({ id: id2, result: 'result2' }) + '\n'));
        mockProc.stdout.emit('data', Buffer.from(JSON.stringify({ id: id1, result: 'result1' }) + '\n'));
        expect(await p1).toBe('result1');
        expect(await p2).toBe('result2');
        bridge.dispose();
    });
    test('call() rejects when backend returns error response', async () => {
        const bridge = new bridge_1.Bridge('python3', '/path/to/backend_server.py');
        await bridge.start();
        const promise = bridge.call('analyze_efficiency', { code: '' });
        const written = mockProc.stdin.write.mock.calls[0][0];
        const { id } = JSON.parse(written.trim());
        mockProc.stdout.emit('data', Buffer.from(JSON.stringify({ id, error: { message: 'Code is empty', type: 'ValueError' } }) + '\n'));
        await expect(promise).rejects.toThrow('ValueError: Code is empty');
        bridge.dispose();
    });
    test('dispose() rejects all pending promises', async () => {
        const bridge = new bridge_1.Bridge('python3', '/path/to/backend_server.py');
        await bridge.start();
        const promise = bridge.call('analyze_efficiency', { code: 'x = 1' });
        bridge.dispose();
        await expect(promise).rejects.toThrow('Bridge disposed');
    });
    test('dispose() kills the process', async () => {
        const bridge = new bridge_1.Bridge('python3', '/path/to/backend_server.py');
        await bridge.start();
        bridge.dispose();
        expect(mockProc.kill).toHaveBeenCalled();
    });
});
//# sourceMappingURL=bridge.test.js.map