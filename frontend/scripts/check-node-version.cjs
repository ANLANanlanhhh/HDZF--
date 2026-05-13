const [major, minor] = process.versions.node.split('.').map(Number)

const supported =
  major === 20 ||
  major === 22 ||
  (major === 24 && minor >= 14)

if (!supported) {
  console.error(
    `Unsupported Node.js ${process.versions.node}. Use Node.js 22 LTS, or Node.js 24.14.0+ if you must use Node 24.`
  )
  process.exit(1)
}
