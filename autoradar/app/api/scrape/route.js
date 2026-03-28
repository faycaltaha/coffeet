import { NextResponse } from 'next/server';
import { supabaseAdmin } from '@/lib/supabase';
import { scrapeListings } from '@/lib/scraper';

export async function POST(request) {
  try {
    const { search_id } = await request.json();

    if (!search_id) {
      return NextResponse.json({ error: 'search_id requis' }, { status: 400 });
    }

    // Récupérer les paramètres de recherche depuis Supabase
    const { data: search, error: searchError } = await supabaseAdmin
      .from('searches')
      .select('*')
      .eq('id', search_id)
      .single();

    if (searchError || !search) {
      return NextResponse.json({ error: 'Recherche introuvable' }, { status: 404 });
    }

    // Lancer le scraping
    const listings = await scrapeListings({
      marque: search.marque,
      budget_max: search.budget_max,
      km_max: search.km_max,
      annee_min: search.annee_min,
      annee_max: search.annee_max,
      carburant: search.carburant,
      region: search.region,
    });

    if (listings.length === 0) {
      return NextResponse.json({ success: true, count: 0 });
    }

    // Supprimer les anciennes annonces de cette recherche avant d'insérer les nouvelles
    await supabaseAdmin
      .from('listings')
      .delete()
      .eq('search_id', search_id);

    // Préparer les données à insérer
    const rows = listings.map((l) => ({
      search_id,
      titre: l.titre,
      prix: l.prix,
      kilometrage: l.kilometrage,
      annee: l.annee,
      carburant: l.carburant,
      localisation: l.localisation,
      url: l.url,
      image_url: l.image_url,
      score: null,       // calculé par IA dans une étape ultérieure
      score_label: null,
      scraped_at: new Date().toISOString(),
    }));

    const { error: insertError } = await supabaseAdmin
      .from('listings')
      .insert(rows);

    if (insertError) {
      console.error('[api/scrape] Erreur insertion:', insertError.message);
      return NextResponse.json({ error: 'Erreur sauvegarde listings' }, { status: 500 });
    }

    return NextResponse.json({ success: true, count: rows.length });
  } catch (err) {
    console.error('[api/scrape] Erreur inattendue:', err.message);
    return NextResponse.json({ error: 'Erreur serveur' }, { status: 500 });
  }
}
