#!/usr/bin/env node

const { spawnSync } = require("node:child_process");

const REPO_URL = "https://github.com/yaoruiquan/vulns_skills.git";

function printHelp() {
  console.log(`Install Product Security Research AI-Skills.

Usage:
  npx @yaoruiquan4/vulns-skills
  npx @yaoruiquan4/vulns-skills -- --help

This package is only a lightweight installer. It does not bundle the skills.
It runs:
  claude skills install ${REPO_URL}
`);
}

if (process.argv.includes("--help") || process.argv.includes("-h")) {
  printHelp();
  process.exit(0);
}

const result = spawnSync("claude", ["skills", "install", REPO_URL], {
  stdio: "inherit"
});

if (result.error) {
  console.error("\nFailed to run `claude skills install`.");
  console.error("Make sure Claude Code is installed and available in PATH:");
  console.error("  claude --version");
  console.error("\nThen install manually:");
  console.error(`  claude skills install ${REPO_URL}`);
  process.exit(1);
}

process.exit(result.status ?? 0);
