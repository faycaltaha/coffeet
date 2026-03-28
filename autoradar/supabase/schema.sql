-- AutoRadar — Schéma Supabase
-- À exécuter dans l'éditeur SQL de Supabase

-- Table searches : configurations de recherche par utilisateur
create table if not exists searches (
  id          uuid primary key default gen_random_uuid(),
  user_id     uuid references auth.users(id) on delete cascade not null,
  marque      text,
  budget_max  integer,
  km_max      integer,
  annee_min   integer,
  annee_max   integer,
  carburant   text check (carburant in ('essence', 'diesel', 'hybride', 'electrique')),
  region      text,
  created_at  timestamp with time zone default now()
);

-- Index pour retrouver les recherches d'un utilisateur rapidement
create index searches_user_id_idx on searches(user_id);

-- RLS : chaque utilisateur ne voit que ses propres recherches
alter table searches enable row level security;

create policy "Utilisateur voit ses recherches"
  on searches for all
  using (auth.uid() = user_id);


-- Table listings : annonces scrapées pour une recherche
create table if not exists listings (
  id            uuid primary key default gen_random_uuid(),
  search_id     uuid references searches(id) on delete cascade not null,
  titre         text,
  prix          integer,
  kilometrage   integer,
  annee         integer,
  carburant     text,
  localisation  text,
  url           text,
  image_url     text,
  score         integer check (score >= 0 and score <= 100),
  score_label   text check (score_label in ('Bon deal', 'Correct', 'À éviter')),
  scraped_at    timestamp with time zone default now()
);

-- Index pour retrouver les annonces d'une recherche, triées par score
create index listings_search_id_score_idx on listings(search_id, score desc);

-- RLS : visible uniquement par le propriétaire de la recherche liée
alter table listings enable row level security;

create policy "Utilisateur voit ses annonces"
  on listings for all
  using (
    exists (
      select 1 from searches
      where searches.id = listings.search_id
        and searches.user_id = auth.uid()
    )
  );
