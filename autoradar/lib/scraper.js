import puppeteer from 'puppeteer';

// Mapping des carburants vers les valeurs LaCentrale
const CARBURANT_MAP = {
  essence: '1',
  diesel: '2',
  hybride: '3',
  electrique: '5',
};

// Mapping simplifié des régions vers les codes département/région LaCentrale
const REGION_MAP = {
  'île-de-france': '75,77,78,91,92,93,94,95',
  'auvergne-rhône-alpes': '01,03,07,15,26,38,42,43,63,69,73,74',
  'provence-alpes-côte-d\'azur': '04,05,06,13,83,84',
  'occitanie': '09,11,12,30,31,32,34,46,48,65,66,81,82',
  'nouvelle-aquitaine': '16,17,19,23,24,33,40,47,64,79,86,87',
  'bretagne': '22,29,35,56',
  'normandie': '14,27,50,61,76',
  'hauts-de-france': '02,59,60,62,80',
  'grand-est': '08,10,51,52,54,55,57,67,68,88',
  'pays-de-la-loire': '44,49,53,72,85',
  'centre-val-de-loire': '18,28,36,37,41,45',
  'bourgogne-franche-comté': '21,25,39,58,70,71,89,90',
};

/**
 * Construit l'URL de recherche LaCentrale avec les filtres.
 */
function buildUrl(params) {
  const { marque, budget_max, km_max, annee_min, annee_max, carburant, region } = params;

  const base = 'https://www.lacentrale.fr/listing';
  const query = new URLSearchParams();

  if (marque) query.set('makesModelsCommercialNames', marque.toUpperCase());
  if (budget_max) query.set('priceMax', String(budget_max));
  if (km_max) query.set('mileageMax', String(km_max));
  if (annee_min) query.set('yearMin', String(annee_min));
  if (annee_max) query.set('yearMax', String(annee_max));
  if (carburant && CARBURANT_MAP[carburant]) query.set('energies', CARBURANT_MAP[carburant]);
  if (region) {
    const depts = REGION_MAP[region.toLowerCase()];
    if (depts) query.set('departments', depts);
  }

  query.set('sortBy', 'creationDate');
  query.set('sortOrder', 'desc');

  return `${base}?${query.toString()}`;
}

/**
 * Extrait les annonces depuis la page LaCentrale chargée dans Puppeteer.
 */
async function extractListings(page) {
  return page.evaluate(() => {
    const cards = document.querySelectorAll('[data-cy="adCard"]');
    const results = [];

    cards.forEach((card) => {
      try {
        const titre = card.querySelector('[data-cy="adCardTitle"]')?.textContent?.trim() || '';
        const prixText = card.querySelector('[data-cy="adCardPrice"]')?.textContent?.replace(/\s/g, '').replace('€', '') || '0';
        const prix = parseInt(prixText, 10) || 0;

        const details = card.querySelectorAll('[data-cy="adCardDetail"]');
        let kilometrage = 0;
        let annee = 0;
        let carburant = '';

        details.forEach((d) => {
          const txt = d.textContent.trim();
          if (txt.includes('km')) kilometrage = parseInt(txt.replace(/\s/g, '').replace('km', ''), 10) || 0;
          else if (/^\d{4}$/.test(txt)) annee = parseInt(txt, 10);
          else if (['Essence', 'Diesel', 'Hybride', 'Electrique'].some(f => txt.includes(f))) carburant = txt;
        });

        const localisation = card.querySelector('[data-cy="adCardLocation"]')?.textContent?.trim() || '';
        const linkEl = card.querySelector('a[href]');
        const url = linkEl ? 'https://www.lacentrale.fr' + linkEl.getAttribute('href') : '';
        const image_url = card.querySelector('img')?.getAttribute('src') || '';

        if (titre && prix > 0) {
          results.push({ titre, prix, kilometrage, annee, carburant, localisation, url, image_url });
        }
      } catch {
        // annonce malformée, on ignore
      }
    });

    return results;
  });
}

/**
 * Scrape les annonces LaCentrale selon les paramètres de recherche.
 * @param {Object} searchParams - { marque, budget_max, km_max, annee_min, annee_max, carburant, region }
 * @returns {Promise<Array>} tableau d'annonces
 */
export async function scrapeListings(searchParams) {
  let browser;

  try {
    browser = await puppeteer.launch({
      headless: 'new',
      args: [
        '--no-sandbox',
        '--disable-setuid-sandbox',
        '--disable-dev-shm-usage',
        '--disable-gpu',
        '--no-first-run',
        '--no-zygote',
        '--single-process',
      ],
    });

    const page = await browser.newPage();

    // User-agent réaliste pour éviter les blocages
    await page.setUserAgent(
      'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
    );

    await page.setViewport({ width: 1280, height: 900 });

    const url = buildUrl(searchParams);
    console.log('[scraper] URL:', url);

    await page.goto(url, { waitUntil: 'networkidle2', timeout: 30000 });

    // Fermer le bandeau cookies si présent
    try {
      const cookieBtn = await page.$('#didomi-notice-agree-button');
      if (cookieBtn) await cookieBtn.click();
      await page.waitForTimeout(1000);
    } catch {
      // pas de bandeau, on continue
    }

    // Attendre les cartes d'annonces
    await page.waitForSelector('[data-cy="adCard"]', { timeout: 15000 });

    const listings = await extractListings(page);
    console.log(`[scraper] ${listings.length} annonces trouvées`);

    return listings;
  } catch (err) {
    console.error('[scraper] Erreur:', err.message);
    return [];
  } finally {
    if (browser) await browser.close();
  }
}
