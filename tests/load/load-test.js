/**
 * k6 load test — Agent Service
 * Run:  k6 run tests/load/load-test.js
 * Tune: k6 run tests/load/load-test.js --vus 50 --duration 60s
 */
import { check, sleep } from "k6";
import http from "k6/http";
import { Rate, Trend } from "k6/metrics";

const errorRate = new Rate("errors");
const agentLatency = new Trend("agent_latency");

export const options = {
  stages: [
    { duration: "10s", target: 10 },  // ramp up
    { duration: "30s", target: 20 },  // sustain
    { duration: "10s", target: 0 },   // ramp down
  ],
  thresholds: {
    http_req_duration: ["p(95)<30000"], // 30s (LLM calls are slow)
    errors: ["rate<0.1"],              // <10% error rate
  },
};

const AGENT_URL = __ENV.AGENT_URL || "http://localhost:8010";
const TOOLS_URL = __ENV.TOOLS_URL || "http://localhost:8011";

const prompts = [
  "What is 2 + 2?",
  "What time is it?",
  "Calculate 100 * 42",
  "Hello, who are you?",
  "What day is today?",
];

export default function () {
  // ── Tools math (fast) ──
  const mathRes = http.post(
    `${TOOLS_URL}/tools/math`,
    JSON.stringify({ expression: "42 * " + Math.floor(Math.random() * 100) }),
    { headers: { "Content-Type": "application/json" }, timeout: "10s" }
  );
  check(mathRes, { "math 200": (r) => r.status === 200 });
  errorRate.add(mathRes.status !== 200);

  // ── Agent run (slow — involves LLM) ──
  const prompt = prompts[Math.floor(Math.random() * prompts.length)];
  const agentRes = http.post(
    `${AGENT_URL}/run`,
    JSON.stringify({
      prompt: prompt,
      sessionId: `load-test-${__VU}-${__ITER}`,
    }),
    { headers: { "Content-Type": "application/json" }, timeout: "120s" }
  );
  check(agentRes, { "agent 200": (r) => r.status === 200 });
  errorRate.add(agentRes.status !== 200);
  agentLatency.add(agentRes.timings.duration);

  sleep(1);
}

export function handleSummary(data) {
  return {
    stdout: textSummary(data, { indent: "  ", enableColors: true }),
  };
}

// k6 has built-in textSummary in newer versions
function textSummary(data) {
  return JSON.stringify(data, null, 2);
}
