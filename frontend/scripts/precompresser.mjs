// Pré-compression du build (gzip 9 + brotli 11) pour gzip_static / brotli_static
// de nginx : un .gz et un .br à côté de chaque fichier compressible, aucun CPU au
// moment de servir. zlib de Node : rien à télécharger en CI (pas d'apt-get brotli).
//
// Usage : node scripts/precompresser.mjs dist/frontend/browser
import { readdirSync, readFileSync, statSync, writeFileSync } from 'node:fs';
import { extname, join } from 'node:path';
import { brotliCompressSync, constants, gzipSync } from 'node:zlib';

const COMPRESSIBLES = new Set([
  '.js',
  '.mjs',
  '.css',
  '.html',
  '.svg',
  '.json',
  '.txt',
  '.xml',
  '.ico',
]);
const TAILLE_MIN = 256;

const racine = process.argv[2];
if (!racine) {
  console.error('usage : node scripts/precompresser.mjs <dossier>');
  process.exit(2);
}

let n = 0;
function parcourir(dossier) {
  for (const nom of readdirSync(dossier)) {
    const chemin = join(dossier, nom);
    if (statSync(chemin).isDirectory()) {
      parcourir(chemin);
    } else if (COMPRESSIBLES.has(extname(nom).toLowerCase())) {
      const contenu = readFileSync(chemin);
      if (contenu.length < TAILLE_MIN) continue;
      writeFileSync(`${chemin}.gz`, gzipSync(contenu, { level: 9 }));
      writeFileSync(
        `${chemin}.br`,
        brotliCompressSync(contenu, {
          params: {
            [constants.BROTLI_PARAM_QUALITY]: 11,
            [constants.BROTLI_PARAM_SIZE_HINT]: contenu.length,
          },
        }),
      );
      n += 1;
    }
  }
}

parcourir(racine);
console.log(`[precompresser] ${n} fichiers compressés (.gz + .br) sous ${racine}`);
