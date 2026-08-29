from __future__ import annotations

import pandas as pd

from scripts.rank_primary_pathway_contributors import PRIMARY_PATHWAYS, rank_primary_contributors


def test_rank_primary_contributors_uses_all_frb_samples_in_group_mean() -> None:
    contributions = pd.DataFrame(
        {
            "function": [PRIMARY_PATHWAYS[0], PRIMARY_PATHWAYS[0], PRIMARY_PATHWAYS[0]],
            "resolved_taxon": ["Genus_a", "Genus_a", "Genus_b"],
            "group": ["Fermented_ricebran", "Fermented_ricebran", "control"],
            "value": [8.0, 4.0, 100.0],
        }
    )
    pathways = pd.DataFrame({"pathway": [PRIMARY_PATHWAYS[0]], "pathway_name": ["chorismate"]})

    ranked = rank_primary_contributors(
        contributions,
        pathways,
        group_sizes={"control": 4, "ricebran": 4, "Fermented_ricebran": 4},
        top_n=20,
    )

    genus_a = ranked.set_index("resolved_taxon").loc["Genus_a"]
    assert genus_a["target_group"] == "Fermented_ricebran"
    assert genus_a["target_group_mean"] == 3.0
    assert genus_a["target_group_fraction"] == 1.0
