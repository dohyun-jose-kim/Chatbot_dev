============================================================
  Fishery Byproduct Bioactivity — RAG Chatbot
  PubMed paper-grounded Q&A system
============================================================
  Commands:
    quit / q       Exit
    k <number>     Change top-K (default: 5)
    papers         Show last retrieved papers
    help           Show this message
============================================================

Loading models...
Retriever ready (device: mps, docs: 5,590)
LLM ready (Claude: claude-haiku-4-5-20251001)
Ready!


Query> huggingface/tokenizers: The current process just got forked, after parallelism has already been used. Disabling parallelism to avoid deadlocks...
To disable this warning, you can either:
	- Avoid using `tokenizers` before the fork if possible
	- Explicitly set the environment variable TOKENIZERS_PARALLELISM=(true | false)
huggingface/tokenizers: The current process just got forked, after parallelism has already been used. Disabling parallelism to avoid deadlocks...
To disable this warning, you can either:
	- Avoid using `tokenizers` before the fork if possible
	- Explicitly set the environment variable TOKENIZERS_PARALLELISM=(true | false)

  Searching (top-5)...
  Found 5 papers (1.2s)
    [1] PMID:29874447 | Biologically Active Substances from Marine Hydrobionts with ...
    [2] PMID:28923565 | Chitin and chitosan preparation from shrimp shells Penaeus m...
    [3] PMID:37295482 | Investigation on anti-quorum sensing activities of chitosan ...
    [4] PMID:29800672 | Skin protectant textiles loaded with fish collagen, chitosan...
    [5] PMID:26977152 | Synthesis and Characterization of Chitosan Nanoaggregates fr...

  Generating answer...

────────────────────────────────────────────────────────────
# Antimicrobial Activity of Chitosan from Crustacean Shells

## Key Findings

Chitosan extracted from crustacean shells demonstrates significant antimicrobial activity against various pathogenic bacteria and fungi, making it a promising natural bioactive compound for pharmaceutical and protective applications.

## Supporting Details by Paper

### Antimicrobial Efficacy Against Specific Pathogens

**Shrimp Shell Chitosan:** Chitosan extracted from shrimp shells (*Penaeus monodon*) showed notable antimicrobial properties, with application potential in pharmaceutical industries (PMID: 28923565). When loaded onto textile fabrics, chitosan from shrimp shells exhibited antimicrobial action against both antibiotic-sensitive and antibiotic-resistant strains of *Staphylococcus aureus* and *Candida albicans* (PMID: 29800672).

**Enhanced Activity in Composite Formulations:** Combined chitosan extracts demonstrated superior antimicrobial effects compared to individual treatments. Textiles loaded with composite extracts of fish collagen, shrimp-derived chitosan, and oak gall extract were most effective, followed by individual oak gall extract and chitosan treatments alone (PMID: 29800672).

**Durability:** Treated textiles maintained most of their antimicrobial activity against skin pathogens after 2 laundering cycles (PMID: 29800672).

### Advanced Formulations and Mechanisms

**Chitosan Nanoaggregates:** Chitosan nanoaggregates synthesized from squid gladius showed significant antimicrobial inhibition rates against *Staphylococcus aureus* and *Escherichia coli*, attributed to high cellular uptake (PMID: 26977152).

**Synergistic Approach:** Chitosan from crustacean shells (Squilla) combined with silver nanoparticles and immobilized chitosanase enzyme demonstrated enhanced antimicrobial and quorum-quenching effects against multi-drug resistant (MDR) pathogens, with effectiveness in eliminating biofilm formation (PMID: 37295482).

**Wound Dressing Applications:** Gel wound dressings based on chitosan and calcium alginate containing bioactive substances showed pronounced antibacterial effects against *Staphylococcus aureus* infection in a thermal burn model (PMID: 29874447).

## Cited Papers

1. PMID: 29874447 - Antibiotics and chemotherapy (2016)
2. PMID: 28923565 - International journal of biological macromolecules (2018)
3. PMID: 37295482 - Microbial pathogenesis (2023)
4. PMID: 29800672 - International journal of biological macromolecules (2018)
5. PMID: 26977152 - International journal of biomaterials (2016)
────────────────────────────────────────────────────────────
  (search 1.2s + generation 6.6s)

Query> 