import { spawnSync } from "node:child_process";
import { fileURLToPath } from "node:url";
import path from "node:path";

const e2eRoot = path.resolve(path.dirname(fileURLToPath(import.meta.url)), "..");
const repoRoot = path.resolve(e2eRoot, "..");
const composeFile = path.join(repoRoot, "docker-compose.e2e.yml");
const live = process.argv.includes("--live");

if (live && !process.env.OPENAI_API_KEY) {
  console.error("OPENAI_API_KEY is required for npm run test:live.");
  process.exit(2);
}

const environment = {
  ...process.env,
  E2E_AI_MODE: live ? "live" : "fake",
  E2E_IMAGE_MODE: live ? "live" : "fake",
  E2E_LIVE: live ? "true" : "false",
};

function run(command, args, options = {}) {
  const result = spawnSync(command, args, {
    cwd: options.cwd || repoRoot,
    env: environment,
    stdio: "inherit",
    shell: false,
  });
  if (result.error) console.error(result.error.message);
  return result;
}

const compose = (...args) => run("docker", ["compose", "-f", composeFile, ...args]);
let exitCode = 1;

try {
  // A fixed Compose project is safe because it owns only disposable E2E resources.
  compose("down", "--volumes", "--remove-orphans");
  const started = compose("up", "--build", "--wait", "--wait-timeout", live ? "600" : "240");
  if (started.status !== 0) {
    compose("logs", "--no-color");
    throw new Error("The E2E application stack did not become healthy.");
  }

  const playwrightCli = path.join(
    e2eRoot,
    "node_modules",
    "@playwright",
    "test",
    "cli.js",
  );
  const tested = run(process.execPath, [playwrightCli, "test"], { cwd: e2eRoot });
  exitCode = tested.status ?? 1;
} catch (error) {
  console.error(error instanceof Error ? error.message : error);
  exitCode = 1;
} finally {
  const stopped = compose("down", "--volumes", "--remove-orphans");
  if (stopped.status !== 0 && exitCode === 0) exitCode = stopped.status ?? 1;
}

process.exit(exitCode);
