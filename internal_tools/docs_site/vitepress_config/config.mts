// llamatron: a music program
// Copyright (C) 2026  Michael DeHaan
//
// This program is free software: you can redistribute it and/or modify
// it under the terms of the GNU General Public License as published by
// the Free Software Foundation, either version 3 of the License, or
// (at your option) any later version.
//
// This program is distributed in the hope that it will be useful,
// but WITHOUT ANY WARRANTY; without even the implied warranty of
// MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
// GNU General Public License for more details.
//
// You should have received a copy of the GNU General Public License
// along with this program.  If not, see <https://www.gnu.org/licenses/>.

// The documentation website's VitePress config. internal_tools/build_docs.sh copies it into .docs_site/site,
// the staging folder, beside the pages internal_tools/stage_docs_site.py stages, with the sidebar it writes from GUIDE.md.

import { readFileSync } from 'node:fs'
import { withMermaid } from 'vitepress-plugin-mermaid'

const sidebar = JSON.parse(readFileSync(new URL('../sidebar.json', import.meta.url), 'utf-8'))

export default withMermaid({
  title: 'llamatron',
  description: 'A tracker for composing music in MIDI, played live, recorded, or exported to Ableton Live.',
  // GitHub Pages serves the repository's site under its name.
  base: '/llamatron/',
  outDir: process.env.LLAMATRON_SITE_OUT,
  cleanUrls: true,
  lastUpdated: false,
  // The chapters link only to each other and the front page; a link outside them is left for GitHub to serve.
  ignoreDeadLinks: true,
  themeConfig: {
    nav: [
      { text: 'Home', link: '/' },
      { text: 'Demo Songs', link: '/DEMOS' },
      { text: 'Concepts', link: '/CONCEPTS' },
    ],
    sidebar,
    search: { provider: 'local' },
    outline: { level: [2, 3] },
    socialLinks: [{ icon: 'github', link: 'https://github.com/mpdehaan/llamatron' }],
    footer: { message: 'Released under the GNU General Public License, version 3 or later.' },
  },
})
