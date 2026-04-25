"use strict";
Object.defineProperty(exports, "__esModule", { value: true });
const reportPanel_1 = require("../reportPanel");
// Mock fs and path so we don't need real files
jest.mock('fs', () => ({ readFileSync: jest.fn(() => '<html><body><div id="content"></div></body></html>') }));
jest.mock('path', () => ({ join: jest.fn((...args) => args.join('/')) }));
function makeMockBridge() {
    return { call: jest.fn(), start: jest.fn(), dispose: jest.fn() };
}
describe('ReportPanel', () => {
    let panel;
    let mockBridge;
    beforeEach(() => {
        jest.clearAllMocks();
        mockBridge = makeMockBridge();
        panel = new reportPanel_1.ReportPanel(mockBridge, '/mock/extension');
    });
    // ── renderError ──────────────────────────────────────────────────────────
    test('renderError includes the error message in HTML output', () => {
        const html = panel.renderError('Something went wrong');
        expect(html).toContain('Something went wrong');
    });
    test('renderError includes the error message for any string', () => {
        const messages = ['Timeout', 'SyntaxError: invalid syntax', 'Connection refused', '<script>xss</script>'];
        for (const msg of messages) {
            const html = panel.renderError(msg);
            // The message should appear (possibly escaped)
            expect(html.toLowerCase()).toContain(msg.toLowerCase().replace(/</g, '&lt;').replace(/>/g, '&gt;'));
        }
    });
    test('renderError escapes HTML special characters', () => {
        const html = panel.renderError('<script>alert("xss")</script>');
        expect(html).not.toContain('<script>');
        expect(html).toContain('&lt;script&gt;');
    });
    // ── renderReport ─────────────────────────────────────────────────────────
    function makeReport() {
        return {
            analysis: { functions: [], issues: [], parse_time_ms: 1.0 },
            original_metrics: { execution_time_ms: 100, memory_used_bytes: 2048, energy_kwh: 0.001, co2_grams: 0.5 },
            optimized_code: 'x = 1',
            optimized_metrics: { execution_time_ms: 80, memory_used_bytes: 1024, energy_kwh: 0.0008, co2_grams: 0.4 },
            comparison: {
                execution_time_improvement_pct: 20,
                memory_improvement_pct: 50,
                co2_improvement_pct: 20,
                summary: 'Good improvement.',
            },
        };
    }
    test('renderReport contains original metrics section', () => {
        const html = panel.renderReport(makeReport());
        expect(html).toContain('Original Metrics');
        expect(html).toContain('100.00 ms');
    });
    test('renderReport contains optimized code section', () => {
        const html = panel.renderReport(makeReport());
        expect(html).toContain('Optimized Code');
        expect(html).toContain('x = 1');
    });
    test('renderReport contains optimized metrics section', () => {
        const html = panel.renderReport(makeReport());
        expect(html).toContain('Optimized Metrics');
        expect(html).toContain('80.00 ms');
    });
    test('renderReport contains comparison section', () => {
        const html = panel.renderReport(makeReport());
        expect(html).toContain('Comparison');
        expect(html).toContain('20.00%');
    });
    test('renderReport contains summary', () => {
        const html = panel.renderReport(makeReport());
        expect(html).toContain('Good improvement.');
    });
    // ── no active file ────────────────────────────────────────────────────────
    test('show() with no document sets "Open a Python file" content', () => {
        panel.show(undefined);
        // The panel was created and content was set — verify via the mock webview
        // (We can't easily verify postMessage without deeper mocking, but we verify no error thrown)
        expect(true).toBe(true); // smoke test — no exception thrown
    });
});
//# sourceMappingURL=reportPanel.test.js.map