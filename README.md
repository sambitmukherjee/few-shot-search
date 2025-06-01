# few-shot-search
Official code base for the paper titled **"Few-Shot Search: In-Context Learning for Tree and Graph Search."**

This repository contains code for:
- Performing few-shot search using DFS and A* on two domains: Game of 24 and Maze Navigation.
- Generating and accessing datasets and model outputs.
- Reproducing evaluation results from the main paper.
- Running the experiments and few-shot examples used in the study.

## Setup
```
# Clone the repository
git clone https://github.com/sambitmukherjee/few-shot-search.git
cd few-shot-search

# Create virtual environment
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt
```

## Repository Structure
```
few-shot-search/
├── demos/                                # Interactive demo notebooks
│   ├── few_shot_search_game_of_24_dfs.ipynb
│   └── few_shot_search_maze_navigation_a_star.ipynb
│
├── eval/                                 # Evaluation results and datasets
│   ├── eval_notebooks/                   # Placeholder for domain-wise eval notebooks
│   │   ├── game_of_24/
│   │   └── maze_navigation/
│   │
│   ├── game_of_24/
│   │   ├── gpt-4o/
│   │   │   ├── eval/
│   │   │   │   └── eval_set_24.csv
│   │   │   ├── game_24_gpt-4o_gamewise_failure_count.csv
│   │   │   ├── game_24_gpt-4o_gamewise_final_answer.csv
│   │   │   ├── game_24_gpt-4o_gamewise_interleaved_table.csv
│   │   │   ├── game_24_gpt-4o_gamewise_total_count.csv
│   │   │   └── game_24_puzzle_results.csv
│   │   │
│   │   └── gpt-4o-mini/
│   │       ├── eval/
│   │       │   └── eval_set_24.csv
│   │       ├── game_24_gpt-4o-mini_gamewise_failure_count.csv
│   │       ├── game_24_gpt-4o-mini_gamewise_final_answer.csv
│   │       ├── game_24_gpt-4o-mini_gamewise_interleaved_table.csv
│   │       └── game_24_gpt-4o-mini_gamewise_total_count.csv
│   │
│   └── maze_navigation/
│       ├── attributes_gpt_4o.csv
│       ├── attributes_gpt_4o_mini.csv
│       ├── solve_rate_gpt_4o.csv
│       └── solve_rate_gpt_4o_mini.csv
│
├── few_shot_examples/                    # Core few-shot prompt templates
│   ├── game_of_24_dfs_4_shot_examples.py
│   └── maze_navigation_a_star_2_shot_examples.py
│
├── logs/                                 # Run logs from experiments
│   ├── game_of_24_dfs/
│   └── maze_navigation_a_star/
│
├── LICENSE
└── README.md
```
## How To Run
### Run Demos
Game of 24 (DFS Search)\
```demos/few_shot_search_game_of_24_dfs.ipynb```

Maze Navigation (A* Search)\
```demos/few_shot_search_maze_navigation_a_star.ipynb```


### Run Evaluation
Game of 24 (DFS Search)\
```eval/eval_notebooks/game_of_24/ICL_DFS_Game_of_24_eval_data_preparation_github_uploaded.ipynb```\
```eval/eval_notebooks/game_of_24/ICL_DFS_Game_of_24_Evaluation_Framework_github_uploaded.ipynb```

Maze Navigation (A* Search)\
```eval/eval_notebooks/maze_navigation/gpt-4o-trace-generation.ipynb```\
```eval/eval_notebooks/maze_navigation/A_star_ Complete_Eval.py```

