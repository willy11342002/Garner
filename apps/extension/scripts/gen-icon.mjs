import sharp from "sharp"
import { readFileSync, mkdirSync } from "fs"
import { resolve, dirname } from "path"
import { fileURLToPath } from "url"

const __dirname = dirname(fileURLToPath(import.meta.url))
const svgPath = resolve(__dirname, "../../web/public/favicon.svg")
const assetsDir = resolve(__dirname, "../assets")
const outPath = resolve(assetsDir, "icon.png")

mkdirSync(assetsDir, { recursive: true })

const svg = readFileSync(svgPath)
await sharp(svg, { density: 300 })
  .resize(512, 512)
  .png()
  .toFile(outPath)

console.log("✓ assets/icon.png generated from favicon.svg")
