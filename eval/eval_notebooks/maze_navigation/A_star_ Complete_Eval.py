import re
from pprint import pprint
from collections import defaultdict
import os
import json
import pandas as pd
import itertools

eval_dict = {}

##### EVAL 1 Check the process
def check_process(all_str_except_plan):
    each_segment = all_str_except_plan.split("~~~")
    process_eval = {}
    step_0_process_correct = ["initialize_heap","initialize_visited","initialize_costs","initialize_path", "costs.update","heap.push","visited.contains","heap.is_empty"]
    caught_inits = []

    def extract_neighbors_list(text):
        """Extract neighbors list from text like 'The neighbors of the current node are: [21]'"""
        match = re.search(r'The neighbors of the current node are: \[([^\]]+)\]', text)
        if match:
            neighbors_str = match.group(1)
            # Handle both single numbers and comma-separated lists
            if ',' in neighbors_str:
                return [int(x.strip()) for x in neighbors_str.split(',')]
            else:
                return [int(neighbors_str.strip())]
        return []

    def check_inequality_with_less_than(text):
        """Check if there's an inequality with '<' sign and extract the values"""
        pattern = r'(\d+(?:\.\d+)?)\s*<\s*(\w+)'
        matches = re.findall(pattern, text)
        return len(matches) > 0

    def validate_astar_step(segment_text):
        """Validate a single A* algorithm step"""
        validation_results = {
            'heap_pop_occurred': False,
            'node_added_to_visited': False,
            'popped_node': None,
            'visited_node': None,
            'neighbors_processed_correctly': True,
            'neighbors_list': [],
            'cost_fetched_for_neighbors': [],
            'inequality_checks': [],
            'costs_updated': [],
            'heap_contains_checked': [],
            'heap_pushed': [],
            'path_updated': [],
            'goal_check': False,
            'heap_empty_check': False
        }

        lines = segment_text.split('\n')

        # Check for heap.pop and extract popped node
        for i, line in enumerate(lines):
            if 'Action: heap.pop()' in line:
                validation_results['heap_pop_occurred'] = True
                # Look for the observation (next few lines)
                for j in range(i+1, min(i+5, len(lines))):
                    if lines[j].strip().isdigit():
                        validation_results['popped_node'] = int(lines[j].strip())
                        break

            # Check if the same node is added to visited
            if 'Action: visited.add(' in line:
                match = re.search(r'visited\.add\((\d+)\)', line)
                if match:
                    validation_results['node_added_to_visited'] = True
                    validation_results['visited_node'] = int(match.group(1))

        # Verify popped node equals visited node
        if (validation_results['popped_node'] is not None and
            validation_results['visited_node'] is not None):
            validation_results['same_node_popped_and_visited'] = (
                validation_results['popped_node'] == validation_results['visited_node']
            )

        # Extract neighbors list
        validation_results['neighbors_list'] = extract_neighbors_list(segment_text)

        # For each neighbor, check the required conditions
        neighbors_with_better_cost = []  # Track neighbors where inequality is true

        for neighbor in validation_results['neighbors_list']:
            neighbor_str = str(neighbor)

            # 1. Check if cost is being fetched (this should always happen)
            cost_fetch_pattern = f'Action: costs\.fetch\(node={neighbor}\)'
            if re.search(cost_fetch_pattern, segment_text):
                validation_results['cost_fetched_for_neighbors'].append(neighbor)

            # 2. Check for inequality with "<" sign and extract the specific neighbor context
            lines = segment_text.split('\n')
            neighbor_section_start = -1
            neighbor_section_end = -1

            for i, line in enumerate(lines):
                if f'The current neighbor is: {neighbor}' in line:
                    neighbor_section_start = i
                elif neighbor_section_start != -1 and ('The current neighbor is:' in line or 'Finished looping' in line):
                    neighbor_section_end = i
                    break

            if neighbor_section_start != -1:
                if neighbor_section_end == -1:
                    neighbor_section_end = len(lines)

                neighbor_section = '\n'.join(lines[neighbor_section_start:neighbor_section_end])
                # Check for inequality in this specific neighbor's section
                if check_inequality_with_less_than(neighbor_section):
                    validation_results['inequality_checks'].append(neighbor)
                    neighbors_with_better_cost.append(neighbor)

                    # Only check these if inequality was true
                    # 3. Check if costs.update is called for this neighbor
                    cost_update_pattern = f'Action: costs\.update\(node={neighbor}'
                    if re.search(cost_update_pattern, neighbor_section):
                        validation_results['costs_updated'].append(neighbor)

                    # 4. Check if heap.contains is checked
                    heap_contains_pattern = f'Action: heap\.contains\({neighbor}\)'
                    if re.search(heap_contains_pattern, neighbor_section):
                        validation_results['heap_contains_checked'].append(neighbor)

                    # 5. Check if heap.push is called for this neighbor
                    heap_push_pattern = f'Action: heap\.push\({neighbor},'
                    if re.search(heap_push_pattern, neighbor_section):
                        validation_results['heap_pushed'].append(neighbor)

                    # 6. Check if path is updated for this neighbor
                    path_update_pattern = f'Action: path\.update\(node={neighbor}'
                    if re.search(path_update_pattern, neighbor_section):
                        validation_results['path_updated'].append(neighbor)

        # Store neighbors that had better costs for later validation
        validation_results['neighbors_with_better_cost'] = neighbors_with_better_cost

        # Check for goal node check (visited.contains(57))
        if 'Action: visited.contains' in segment_text:
            validation_results['goal_check'] = True

        # Check for heap.is_empty() check
        if 'Action: heap.is_empty()' in segment_text:
            validation_results['heap_empty_check'] = True

        if "Yes, the `goal` node" in segment_text:
            validation_results['heap_empty_check'] = True

        return validation_results

    # Main processing loop
    for i, seg in enumerate(each_segment):
        if i == len(each_segment) - 1:

            if ("is empty" in each_segment[i-1]) and ("unsuccessful" in seg):
                process_eval["step_last_process_correct"] = True
            elif ("Yes, the `goal` node" in each_segment[i-1]) and ("Successful".lower() in seg.lower()):
                if "Action: path.trace" in seg:
                    process_eval["step_last_process_correct"] = True
                else:
                    process_eval["step_last_process_correct"] = False
            else:
                process_eval["step_last_process_correct"] = False
            break

        if i == 0:
            # Handle step 1 initialization as before
            for j, l in enumerate(seg.split("\n\n")):
                if "Action:" in l:
                    function_name = l.split("Action:")[1].strip().split("(")[0].strip()
                    caught_inits.append(function_name)

            if caught_inits == step_0_process_correct:
                process_eval["step_0_process_correct"] = True
            else:
                process_eval["step_0_process_correct"] = False
        else:
            # Handle subsequent A* algorithm steps
            validation_results = validate_astar_step(seg)

            # Store results for this step
            step_key = f"step_{i}"
            process_eval[step_key] = validation_results

            # Print validation summary for this step
            # print(f"Step {i} Validation Results:")
            # print(f"  Heap pop occurred: {validation_results['heap_pop_occurred']}")
            # print(f"  Node added to visited: {validation_results['node_added_to_visited']}")
            # print(f"  Same node popped and visited: {validation_results.get('same_node_popped_and_visited', 'N/A')}")
            # print(f"  Neighbors found: {validation_results['neighbors_list']}")
            # print(f"  Cost fetched for all neighbors: {validation_results['cost_fetched_for_neighbors']}")
            # print(f"  Neighbors with better cost (inequality true): {validation_results['neighbors_with_better_cost']}")
            # print(f"  Costs updated (only for better cost): {validation_results['costs_updated']}")
            # print(f"  Heap contains checked (only for better cost): {validation_results['heap_contains_checked']}")
            # print(f"  Heap pushed (only for better cost): {validation_results['heap_pushed']}")
            # print(f"  Path updated (only for better cost): {validation_results['path_updated']}")
            # print(f"  Goal check (visited.contains(goalNode)): {validation_results['goal_check']}")
            # print(f"  Heap empty check: {validation_results['heap_empty_check']}")

            # Check if all neighbors were processed correctly
            neighbors = validation_results['neighbors_list']
            neighbors_with_better_cost = validation_results['neighbors_with_better_cost']
            all_neighbors_correct = True

            # All neighbors should have cost fetched
            for neighbor in neighbors:
                if neighbor not in validation_results['cost_fetched_for_neighbors']:
                    all_neighbors_correct = False
                    print(f"Neighbor {neighbor} missing cost fetch")

            # Only neighbors with better cost should have the other operations
            for neighbor in neighbors_with_better_cost:
                neighbor_correct = (
                    neighbor in validation_results['costs_updated'] and
                    neighbor in validation_results['heap_contains_checked'] and
                    neighbor in validation_results['heap_pushed'] and
                    neighbor in validation_results['path_updated']
                )
                if not neighbor_correct:
                    all_neighbors_correct = False
                    print(f"Neighbor {neighbor} with better cost, missing require processes like cost update, heap_push...")

            process_eval[f"{step_key}_neighbors_correct"] = all_neighbors_correct
            process_eval[f"{step_key}_termination_checks"] = (
                validation_results['goal_check'] and validation_results['heap_empty_check']
            )
    return process_eval
# pprint(check_process(all_str_except_plan))

##### Eval 2 Check if values are consistant, calculations are right and checks are correct
def consistency_calculations_checks_wrt_GT(all_str_except_plan, eval_dict={}):
    sections = split_graph_sections(all_str_except_plan)
    graph, start_node, goal_node, heuristics = parse_graph_data(sections[1])  # GT

    # Use defaultdict(list) to collect multiple occurrences per key
    if eval_dict is None:
        eval_dict = defaultdict(list)
    else:
        temp_dict = defaultdict(list)
        for k, v in eval_dict.items():
            if isinstance(v, list):
                temp_dict[k].extend(v)
            else:
                temp_dict[k].append(v)
        eval_dict = temp_dict

    # Helper to append rather than overwrite
    def log(key, value):
        eval_dict[key].append(value)

    # Initialize algorithm state variables
    current_node = parent_node = None
    gt_goal_reached = heap_empty = False
    heap = [] 
    costs = {}
    path = {}
    visited = set()

    all_lines = all_str_except_plan.split("\n\n")

    def safe_eval_boolean(text):
        try:
            t = text.strip().lower()
            if 'true' in t: return True
            if 'false' in t: return False
            return eval(text.strip())
        except:
            return None

    def safe_get(arr, idx):
        return arr[idx] if 0 <= idx < len(arr) else None

    for i, line in enumerate(all_lines):
        # current neighbor check logged every time
        if "The current neighbor is:" in line:
            curr = line.split(":")[-1].strip()
            if parent_node is not None:
                try:
                    in_graph = int(curr) in eval(graph)[int(parent_node)]
                except:
                    in_graph = False
                log("current_node_taken_from_graph", in_graph)
            current_node = curr
            continue

        # cost calc from 999 collects each evaluation
        if "The previously known cost is" in line and parent_node is not None:
            try:
                gt_cost = int(costs[parent_node])
                nxt = safe_get(all_lines, i+1) or ""
                parts = nxt.split("=")
                if len(parts) >= 3:
                    found_raw = parts[-2].strip().split()[0]
                    found_cost = int(found_raw)
                    lhs_rhs_equal = eval(parts[-2]) == int(parts[-1].strip())
                    new_cost_ok = (gt_cost + 1) == eval(parts[-2])
                    log("cost_in_cost_calc_eqn_check", gt_cost == found_cost)
                    log("final_cost_equation_lhs_equals_rhs", lhs_rhs_equal)
                    log("new_cost_val_in_cost_eqn_check", new_cost_ok)
            except:
                log("cost_in_cost_calc_eqn_check", False)
                log("final_cost_equation_lhs_equals_rhs", False)
                log("new_cost_val_in_cost_eqn_check", False)

        # neighbors list correctness and exploration logged
        if "The neighbors of the current node are:" in line and current_node:
            m = re.search(r"\[([0-9,\s]+)\]", line)
            neigh = []
            if m:
                neigh = list(map(int, m.group(1).split(',')))
            try:
                expected = eval(graph)[int(current_node)]
                log("neighbors_correct_from_graph", neigh == expected)
            except:
                log("neighbors_correct_from_graph", False)

            missing = set(eval(graph).get(int(current_node), []))
            for block in all_lines[i:]:
                if "Finished looping through all the neighbors" in block:
                    break
                if "The current neighbor is:" in block:
                    try:
                        missing.discard(int(block.split(":")[-1]))
                    except:
                        pass
            log("all_neighbors_explored", len(missing) == 0)

        if "Action:" in line:
            act = line.split("Action:")[-1].strip()
            # handling actions locally to update state simulating the realtime events
            if act.startswith("initialize_costs"):
                costs = {str(k): int('999') for k in eval(heuristics)}
            elif act.startswith("initialize_heap"):
                heap = []
            elif act.startswith("initialize_path"):
                path = {}
            elif act.startswith("initialize_visited"):
                visited = set()
            elif act.startswith("costs.update"):
                r = re.search(r"node=(\d+),\s*cost=(\d+)", act)
                if r:
                    costs[r.group(1)] = int(r.group(2))
            elif act.startswith("costs.fetch"):
                r = re.search(r"node=(\d+)", act)
                if r:
                    current_cost = costs.get(r.group(1), int('999'))
            elif act.startswith("heap.push"):
                r = re.search(r"heap\.push\((\d+),\s*(\d+)\)", act)

                if r:
                    heap.append((r.group(1), r.group(2)))
            elif act.startswith("heap.pop"):
                nxt = safe_get(all_lines, i+2) or ''
                node_popped = nxt.strip()
                heap = [h for h in heap if h[0] != node_popped]
                parent_node = current_node = node_popped
            elif act.startswith("heap.is_empty"):
                heap_empty = len(heap) == 0
            elif act.startswith("visited.add"):
                r = re.search(r"visited\.add\((\d+)\)", act)
                if r:
                    visited.add(r.group(1))
            elif act.startswith("path.update"):
                r = re.search(r"node=(\d+),\s*previous_node=(\d+)", act)
                if r:
                    path[r.group(1)] = r.group(2)
            continue

        # inequality check logs every time encountered
        if "newly discovered cost is less than" in line:
            ok = False
            if current_node and parent_node:
                try:
                    old = int(costs[current_node])
                    new = int(costs[parent_node]) + 1
                    resp = safe_get(all_lines, i+2) or ''
                    ok = (("No" in resp and new >= old) or ("Yes" in resp and new < old))
                except Exception as e:
                    ok = False
            log("inequality_newly_discovered_cost_is_less", ok)

        # Estimated value logging for each encounter
        if "Estimated value" in line:
            parts = line.split("=")
            if len(parts) >= 3:
                equation_str = parts[1].strip()
                rhs_str = parts[2].strip()

                tokens = equation_str.split()
                if len(tokens) >= 3:
                    cost_tok, _, heur_tok = tokens[:3]
                    node_id = int(current_node) if current_node is not None else int(start_node)

                    try:
                        actual_cost = int(costs.get(str(node_id), 0))
                    except (KeyError, ValueError):
                        actual_cost = 0

                    try:
                        actual_heuristic = int(eval(heuristics).get(node_id, 0))
                    except (KeyError, ValueError):
                        actual_heuristic = 0

                    gt_estimate_val = actual_cost + actual_heuristic

                    try:
                        rhs_val = int(rhs_str)
                    except ValueError:
                        rhs_val = None

                    lhs_rhs_check = eval(equation_str) == rhs_val if rhs_val is not None else False
                    gt_vs_rhs_check = gt_estimate_val == rhs_val if rhs_val is not None else False

                    log("cost_from_estimate_equation", str(actual_cost) == cost_tok)
                    log("heuristic_from_estimate_equation", str(actual_heuristic) == heur_tok)
                    log("estimate_value_lhs_equals_rhs", lhs_rhs_check)
                    log("calculated_estimate_value_matches_gen_est_val", gt_vs_rhs_check)

        # Base conditions logged every time
        if any(x in line for x in ["continuing the search"]): # , "Therefore, continuing the search."
            res5 = safe_get(all_lines, i-5) or ''
            goal_ok = (goal_node in visited)
            found_goal = safe_eval_boolean(res5)
            if found_goal is not None:
                log("goal_check_", found_goal == goal_ok)

            res1 = safe_get(all_lines, i-1) or ''
            emp_ok = True if len(heap) == 0 else False
            found_emp = safe_eval_boolean(res1)
            if found_emp is not None:
                log("empty_heap_check", found_emp == emp_ok)

            is_cont = "Neither condition is true" in line
            verdict_ok = (not emp_ok and not goal_ok) if is_cont else (emp_ok or goal_ok)
            log("base_case_final_verdict_check", verdict_ok)

        elif any(x in line for x in ["Yes, the `goal` node", "The search was successful!", "Tracing the final path.", "Action: path.trace"]): # Used hack for time constraint
            res1 = safe_get(all_lines, i-1) or ''
            goal_ok = (goal_node in visited)
            found_goal = safe_eval_boolean(res1)
            if found_goal is not None:
                log("goal_check_", found_goal == goal_ok)

            log("empty_heap_check", True)

            log("base_case_final_verdict_check", True)
            log("reached_goal", True)

        elif (any(x in line for x in ["Yes, `heap` is empty", "`heap` is empty", "The search was unsuccessful!"]) and (not "Checking whether `heap` is empty." in line)):
            res5 = safe_get(all_lines, i-5) or ''
            goal_ok = (goal_node in visited)
            found_goal = safe_eval_boolean(res5)
            if found_goal is not None:
                log("goal_check_", found_goal == goal_ok)

            res1 = safe_get(all_lines, i-1) or ''
            emp_ok = True if len(heap) == 0 else False
            found_emp = safe_eval_boolean(res1)
            if found_emp is not None:
                log("empty_heap_check", found_emp == emp_ok)

            is_cont = "Neither condition is true" in line
            verdict_ok = (not emp_ok and not goal_ok) if is_cont else (emp_ok or goal_ok)
            log("base_case_final_verdict_check", verdict_ok)
            log("reached_goal", False)


    return dict(eval_dict)

def get_search_start_correct(dict1, dict2):
    """Checks if the search started correctly."""
    value = dict2.get('step_0_process_correct', 0)
    explanation = f"Value from Dict2['step_0_process_correct'], which is {value}."
    if not isinstance(value, bool):
        value = 1
        explanation = "Dict2['step_0_process_correct'] was missing or not a boolean, defaulted to False."
    if value == True:
        value = 0
    else:
        value = 1
    return (value, 1), explanation

def get_heap_pop_correct(dict1, dict2):
    """Checks if nodes were correctly popped from the heap in each relevant step."""
    num_algorithm_steps = 0
    correct_pops = 0
    explanation_details = []
    missing_key_in_step = False

    for i in range(1, 1000): # Iterate through step_1, step_2 ...
        step_key = f'step_{i}'
        if step_key in dict2 and isinstance(dict2[step_key], dict):
            num_algorithm_steps += 1
            step_data = dict2[step_key]
            if 'heap_pop_occurred' in step_data:
                if step_data['heap_pop_occurred']:
                    correct_pops += 1
                    explanation_details.append(f"Dict2['{step_key}']['heap_pop_occurred'] is True.")
                else:
                    explanation_details.append(f"Dict2['{step_key}']['heap_pop_occurred'] is False.")
            else: 
                missing_key_in_step = True
                explanation_details.append(f"Dict2['{step_key}']['heap_pop_occurred'] is missing.")
        else:
            break # No more numbered steps

    if num_algorithm_steps == 0:
        value = "No algorithm execution steps" # No algorithm execution steps, so no incorrect pops.
        explanation = "No algorithm execution steps (e.g., step_1, step_2) found in Dict2. Assumed correct as no heap pops were expected or made incorrectly."
    elif missing_key_in_step or correct_pops < num_algorithm_steps : # If any key was missing or any pop was false
        value = f"{int(num_algorithm_steps) - int(correct_pops)}"
        explanation = (f"Not all algorithm steps in Dict2 correctly popped from heap. "
                       f"Found {correct_pops} correct pops out of {num_algorithm_steps} steps, with some keys potentially missing. Details: {' '.join(explanation_details)}")
    else: # All steps present and correct
        value = 0
        explanation = f"All {num_algorithm_steps} algorithm steps in Dict2 show 'heap_pop_occurred' as True. Details: {' '.join(explanation_details)}"
    value = value, num_algorithm_steps
    return value, explanation

def get_add_to_visited_correct(dict1, dict2):
    """Checks if nodes were correctly added to the visited set."""
    num_algorithm_steps = 0
    correct_adds = 0
    explanation_details = []
    check_key = 'same_node_popped_and_visited' # This confirms pop and visit match
    missing_key_in_step = False

    for i in range(1, 1000): # Iterate through step_1, step_2 ...
        step_key = f'step_{i}'
        if step_key in dict2 and isinstance(dict2[step_key], dict):
            num_algorithm_steps += 1
            step_data = dict2[step_key]
            if check_key in step_data:
                if step_data[check_key]:
                    correct_adds += 1
                    explanation_details.append(f"Dict2['{step_key}']['{check_key}'] is True.")
                else:
                    explanation_details.append(f"Dict2['{step_key}']['{check_key}'] is False.")
            else:
                missing_key_in_step = True
                explanation_details.append(f"Dict2['{step_key}']['{check_key}'] is missing.")
        else:
            break

    if num_algorithm_steps == 0:
        value = f"No steps"
        explanation = "No algorithm execution steps (e.g., step_1, step_2) found in Dict2. Assumed correct as no nodes were expected to be added to visited set incorrectly."
    elif missing_key_in_step or correct_adds < num_algorithm_steps:
        value = f"{num_algorithm_steps - correct_adds}"
        explanation = (f"Not all algorithm steps in Dict2 correctly added to visited set (checked via '{check_key}'). "
                       f"Found {correct_adds} correct operations out of {num_algorithm_steps} steps, with some keys potentially missing. Details: {' '.join(explanation_details)}")
    else:
        value = 0
        explanation = f"All {num_algorithm_steps} algorithm steps in Dict2 show '{check_key}' as True. Details: {' '.join(explanation_details)}"
    return (value, num_algorithm_steps), explanation


def get_correct_neighbors(dict1, dict2):
    """Checks if neighbors were correctly retrieved."""
    # Part 1: Check Dict1['neighbors_correct_from_graph']
    val_dict1 = False
    exp_dict1 = ""
    d1_key = 'neighbors_correct_from_graph'
    d1_list = dict1.get(d1_key, [])

    processed_any_neighbors_in_d2 = any(
        isinstance(v, dict) and 'neighbors_list' in v for k, v in dict2.items() if k.startswith('step_') and isinstance(v, dict)
    )

    num_falses_d1 = sum(1 for v in d1_list if v is False)
    total_steps_d1 = len(d1_list)

    if not d1_list:
        if not processed_any_neighbors_in_d2:
            val_dict1 = True
            exp_dict1 = f"Dict1['{d1_key}'] is empty, and no neighbor processing occurred in Dict2 steps; assumed True for Dict1 part."
        else:
            val_dict1 = False
            exp_dict1 = f"Dict1['{d1_key}'] is empty despite neighbor processing indicated in Dict2; assumed False for Dict1 part."
    else:
        val_dict1 = all(d1_list)
        exp_dict1 = f"all(Dict1['{d1_key}']) is {val_dict1} (list: {d1_list})."

    # Part 2: Check Dict2 step_X_neighbors_correct flags
    val_dict2 = True
    exp_dict2_details = []
    dict2_checks_present = False
    all_dict2_flags_true = True

    for i in range(1, 1000):
        step_neighbor_key = f'step_{i}_neighbors_correct'
        if step_neighbor_key in dict2:
            dict2_checks_present = True
            current_flag_val = dict2[step_neighbor_key]
            if not isinstance(current_flag_val, bool) or not current_flag_val:
                all_dict2_flags_true = False
            exp_dict2_details.append(f"Dict2['{step_neighbor_key}'] is {current_flag_val}.")
        elif f'step_{i}' not in dict2 and not any(k.startswith(f'step_{i}_') for k in dict2):
            break

    exp_dict2 = ""
    if not dict2_checks_present and processed_any_neighbors_in_d2:
        exp_dict2 = "No step_X_neighbors_correct keys found in Dict2; Dict2 part of check relies on other neighbor processing flags if available."
    elif dict2_checks_present:
        val_dict2 = all_dict2_flags_true
        exp_dict2 = f"All Dict2 step_X_neighbors_correct flags are True: {val_dict2}. Details: {' '.join(exp_dict2_details)}"
    elif not processed_any_neighbors_in_d2:
        exp_dict2 = "No step_X_neighbors_correct keys found and no neighbor processing in Dict2; Dict2 part is consistent."
        val_dict2 = True

    final_value = val_dict1 and val_dict2
    final_explanation = f"Overall Correct Neighbors check: {exp_dict1} {exp_dict2}"

    return (num_falses_d1, total_steps_d1), final_explanation


def get_neighbor_exploration_correct(dict1, dict2):
    """Checks if neighbor exploration was correct."""
    # Part 1: Check Dict1['all_neighbors_explored']
    val_dict1 = False
    exp_dict1 = ""
    d1_key = 'all_neighbors_explored'
    d1_list = dict1.get(d1_key, [])

    processed_any_neighbors_in_d2 = any(
        isinstance(v, dict) and 'neighbors_list' in v for k, v in dict2.items() if k.startswith('step_') and isinstance(v, dict)
    )

    num_false_in_d1 = 0
    total_d1_steps = len(d1_list)

    if not d1_list:
        if not processed_any_neighbors_in_d2:
            val_dict1 = True
            exp_dict1 = f"Dict1['{d1_key}'] is empty, and no neighbor processing occurred in Dict2 steps; assumed True for Dict1 part."
        else:
            val_dict1 = False
            exp_dict1 = f"Dict1['{d1_key}'] is empty despite neighbor processing indicated in Dict2; assumed False for Dict1 part."
    else:
        num_false_in_d1 = d1_list.count(False)
        val_dict1 = all(d1_list)
        exp_dict1 = (
            f"all(Dict1['{d1_key}']) is {val_dict1} (list: {d1_list}). "
            f"Found {num_false_in_d1} False(s) out of {total_d1_steps} steps."
        )

    # Part 2: Check Dict2 step_X['neighbors_processed_correctly']
    val_dict2 = True
    exp_dict2_details = []
    dict2_steps_checked = 0
    all_d2_processing_correct = True
    missing_key_in_step = False

    for i in range(1, 1000): 
        step_key = f'step_{i}'
        if step_key in dict2 and isinstance(dict2[step_key], dict):
            if 'neighbors_list' in dict2[step_key] or 'neighbors_processed_correctly' in dict2[step_key]:
                dict2_steps_checked += 1
                step_data = dict2[step_key]
                if 'neighbors_processed_correctly' in step_data:
                    if not step_data['neighbors_processed_correctly']:
                        all_d2_processing_correct = False
                    exp_dict2_details.append(
                        f"Dict2['{step_key}']['neighbors_processed_correctly'] is {step_data['neighbors_processed_correctly']}."
                    )
                else:
                    all_d2_processing_correct = False
                    missing_key_in_step = True
                    exp_dict2_details.append(
                        f"Dict2['{step_key}']['neighbors_processed_correctly'] is missing."
                    )
        else:
            break

    exp_dict2 = ""
    if not processed_any_neighbors_in_d2:
        val_dict2 = True
        exp_dict2 = "No neighbor processing occurred in Dict2 steps, so Dict2 check for 'neighbors_processed_correctly' is vacuously True."
    elif dict2_steps_checked == 0 and processed_any_neighbors_in_d2:
        val_dict2 = False
        exp_dict2 = "Neighbor processing occurred in Dict2, but no 'neighbors_processed_correctly' flags found in relevant steps. Assumed False for Dict2 part."
    elif dict2_steps_checked > 0:
        val_dict2 = all_d2_processing_correct
        exp_dict2 = (
            f"All relevant Dict2 step_X['neighbors_processed_correctly'] flags are True: {val_dict2} "
            f"(Missing keys count as False). Details: {' '.join(exp_dict2_details)}"
        )

    final_value = val_dict1 and val_dict2
    final_explanation = f"Overall Neighbor Exploration check: {exp_dict1} {exp_dict2}"

    return (num_false_in_d1, total_d1_steps), final_explanation


def get_newly_discovered_cost_correct(dict1, dict2):
    """Checks correctness of newly discovered costs."""
    keys_to_check_d1 = [
        # 'cost_in_cost_calc_eqn_check',
        # 'final_cost_equation_lhs_equals_rhs',
        'new_cost_val_in_cost_eqn_check'
    ]
    all_correct = True
    explanations = []

    cost_calcs_expected_in_d2 = any(
        isinstance(v, dict) and (v.get('inequality_checks') or v.get('costs_updated') or v.get('cost_fetched_for_neighbors'))
        for k, v in dict2.items() if k.startswith('step_') and isinstance(v, dict)
    )

    total_false_count = 0
    total_count = 0

    for d1_key in keys_to_check_d1:
        data_list = dict1.get(d1_key, [])
        is_list_true = False
        current_false_count = data_list.count(False)
        current_list_len = len(data_list)

        total_false_count += current_false_count
        total_count += current_list_len

        if not data_list:
            if cost_calcs_expected_in_d2:
                is_list_true = False
                explanations.append(f"Dict1['{d1_key}'] is empty despite cost calculation activity in Dict2; assumed False for this part.")
            else:
                is_list_true = True
                explanations.append(f"Dict1['{d1_key}'] is empty, and no relevant cost calculation activity noted in Dict2; assumed True for this part.")
        else:
            is_list_true = all(data_list)
            explanations.append(f"all(Dict1['{d1_key}']) is {is_list_true} (list length: {len(data_list)}).")

        if not is_list_true:
            all_correct = False

    final_explanation = "Overall correctness of newly discovered cost: " + " ".join(explanations)
    return (total_false_count, total_count), final_explanation

def get_cost_inequality_check_correct(dict1, dict2):
    """Checks if cost inequality evaluations were correct."""
    d1_key = 'inequality_newly_discovered_cost_is_less'
    data_list = dict1.get(d1_key, [])
    value = False

    false_count = data_list.count(False)
    total_count = len(data_list)

    inequality_checks_performed_in_d2 = any(
        isinstance(v, dict) and v.get('inequality_checks')  
        for k, v in dict2.items() if k.startswith('step_') and isinstance(v, dict)
    )

    if not data_list:
        if inequality_checks_performed_in_d2:
            value = False
            explanation = f"Dict1['{d1_key}'] is empty, but Dict2 indicates inequality checks were performed/expected; assumed False."
        else:
            value = True
            explanation = f"Dict1['{d1_key}'] is empty, and Dict2 indicates no inequality checks were performed/expected; assumed True."
    else:
        value = all(data_list)
        explanation = f"all(Dict1['{d1_key}']) is {value} (list length: {len(data_list)})."

    return (false_count, total_count), explanation


def get_costs_dictionary_update_correct(dict1, dict2):
    """Checks if the costs dictionary was updated correctly."""
    # --- Dict1 check
    key_d1 = 'new_cost_val_in_cost_eqn_check'
    d1_vals = dict1.get(key_d1, [])
    
    false_count = d1_vals.count(False)
    total_count = len(d1_vals)
    
    if d1_vals:
        val_d1 = all(d1_vals)
        exp_d1 = (f"All entries in Dict1['{key_d1}'] are True: {val_d1} "
                  f"(checked {len(d1_vals)} items).")
    else:
        # if empty
        any_updates = any(
            isinstance(v, dict) and v.get('costs_updated')
            for k, v in dict2.items() if k.startswith('step_')
        )
        val_d1 = not any_updates
        exp_d1 = (f"Dict1['{key_d1}'] is empty; "
                  f"{'no updates' if val_d1 else 'updates'} found in Dict2 → "
                  f"treating as {val_d1}.")

    # --- Dict2 check: inequality ↔ costs_updated per step ---
    per_step_ok = []
    details = []
    for k, step in dict2.items():
        if not (k.startswith('step_') and isinstance(step, dict)):
            continue
        ineq = bool(step.get('inequality_checks'))
        upd  = bool(step.get('costs_updated'))
        ok   = (ineq and upd) or (not ineq and not upd)
        per_step_ok.append(ok)
        details.append(
            f"{k}: inequality_checks={ineq}, costs_updated={upd} → {ok}"
        )

    val_d2 = all(per_step_ok) if per_step_ok else True
    exp_d2 = " ; ".join(details) or "No step-data found in Dict2; treated as True."

    # --- Final aggregate ---
    final_value = val_d1 and val_d2
    final_explanation = f"{exp_d1}\nDict2 per‑step coherence:\n  " + exp_d2
    # return final_value, final_explanation

    return (false_count, total_count), final_explanation


def get_estimated_value_calculation_correct(dict1, dict2):
    """Checks correctness of estimated value calculations."""
    keys_to_check_d1 = [
        'cost_from_estimate_equation',
        'heuristic_from_estimate_equation',
        'estimate_value_lhs_equals_rhs',
        'calculated_estimate_value_matches_gen_est_val'
    ]
    all_correct = True
    explanations = []

    estimate_calcs_expected_in_d2 = any(
        isinstance(v, dict) and v.get('heap_pushed')  
        for k, v in dict2.items() if k.startswith('step_') and isinstance(v, dict)
    )

    false_counts = []
    lengths = []

    for d1_key in keys_to_check_d1:
        data_list = dict1.get(d1_key, [])
        false_count = data_list.count(False)
        total_count = len(data_list)
        false_counts.append(false_count)
        lengths.append(total_count)

        is_list_true = False
        if not data_list:
            if estimate_calcs_expected_in_d2:
                is_list_true = False
                explanations.append(
                    f"Dict1['{d1_key}'] is empty despite estimate calculation activity (heap pushes) in Dict2; assumed False for this part.")
            else:
                is_list_true = True
                explanations.append(
                    f"Dict1['{d1_key}'] is empty, and no relevant estimate calculation activity noted in Dict2; assumed True for this part.")
        else:
            is_list_true = all(data_list)
            explanations.append(
                f"all(Dict1['{d1_key}']) is {is_list_true} (list length: {len(data_list)}).")

        if not is_list_true:
            all_correct = False

    max_false_index = false_counts.index(max(false_counts))
    max_false_count = false_counts[max_false_index]
    max_total_count = lengths[max_false_index]

    final_explanation = "Overall correctness of estimated value calculation: " + " ".join(explanations)
    # return all_correct, final_explanation, max_false_count, max_total_count
    return (max_false_count, max_total_count), final_explanation


def get_heap_push_correct(dict1, dict2):
    """Checks if heap pushes were correct.

    Part 1: Verify Dict1’s estimate‐value correctness:
      - Uses 'calculated_estimate_value_matches_gen_est_val'

    Part 2: For each step_* in dict2, require:
      inequality_checks list == heap_pushed list.
    """
    # --- Part 1: Dict1 estimate‐value correctness ---
    key_val = 'calculated_estimate_value_matches_gen_est_val'
    d1_vals = dict1.get(key_val, [])
    if d1_vals:
        val1 = all(d1_vals)
        exp1 = (f"All entries in Dict1['{key_val}'] are True: {val1} "
                f"(checked {len(d1_vals)} items).")
    else:
        any_pushes = any(
            isinstance(s, dict) and s.get('heap_pushed')
            for k, s in dict2.items() if k.startswith('step_')
        )
        val1 = not any_pushes
        exp1 = (f"Dict1['{key_val}'] is empty; "
                f"{'no pushes' if val1 else 'pushes found'} in Dict2 → treating as {val1}.")

    # --- Part 2: Per‐step matching in Dict2 ---
    per_step_results = []
    details = []
    for k, step in dict2.items():
        if not (k.startswith('step_') and isinstance(step, dict)):
            continue
        ineq = step.get('inequality_checks', [])
        pushed = step.get('heap_pushed', [])
        ok = sorted(ineq) == sorted(pushed)
        per_step_results.append(ok)
        details.append(
            f"{k}: inequality_checks={ineq}, heap_pushed={pushed} → match={ok}"
        )

    total_steps = len(per_step_results)
    false_count = per_step_results.count(False)
    exp2 = " ; ".join(details) or "No step_* entries found in Dict2; treated as True."

    # --- Final return ---
    final_explanation = f"{exp1}\nDict2 per‐step comparison:\n  {exp2}"
    return (false_count, total_steps), final_explanation

def get_path_update_correct(dict1, dict2):
    """
    Returns three values:
      1) count_false_in_details: Number of False matches in dict2 step analysis
      2) total_count_in_details: Total number of steps analyzed in dict2  
      3) dict2_exp: Exact explanation string for dict2 analysis
    """
    # ——— Dict1 part 
    ineq_list = dict1.get('inequality_newly_discovered_cost_is_less', [])
    all_bool = all(isinstance(x, bool) for x in ineq_list)
    any_true = any(ineq_list)
    if not ineq_list:
        dict1_ok = True
        dict1_exp = (
            "Dict1['inequality_newly_discovered_cost_is_less'] is empty; "
            "no expected path updates → treated as OK."
        )
    else:
        dict1_ok = all_bool
        dict1_exp = (
            f"All entries in Dict1['inequality_newly_discovered_cost_is_less'] "
            f"are booleans: {all_bool}; "
            f"{'found True entries' if any_true else 'all False'}."
        )
    
    # ——— Dict2 part ———
    per_step_ok = []
    details = []
    for k, step in dict2.items():
        if not (k.startswith('step_') and isinstance(step, dict)):
            continue
        ineq = step.get('inequality_checks', [])
        pu   = step.get('path_updated', [])
        match = sorted(ineq) == sorted(pu)
        per_step_ok.append(match)
        details.append(f"{k}: {ineq} == {pu} → {match}")
    
    dict2_ok = all(per_step_ok) if per_step_ok else True
    dict2_exp = " ; ".join(details) if details else "No step_* entries found; treated as OK."
    
    count_false_in_details = per_step_ok.count(False)
    total_count_in_details = len(per_step_ok)
    
    return (count_false_in_details, total_count_in_details), dict2_exp


def get_search_stop_correct(dict1, dict2):
    """Checks if the search stop Conditionped correctly."""
    d1_check_keys = {
        'goal_check_': "all(Dict1['goal_check_'])",
        'empty_heap_check': "all(Dict1['empty_heap_check'])",
        'base_case_final_verdict_check': "all(Dict1['base_case_final_verdict_check'])"
    }
    all_d1_correct = True
    d1_explanations = []

    search_ran_significantly = ('step_last_process_correct' in dict2) or \
                               any(k.startswith(f'step_') and isinstance(dict2[k], dict) and k not in ['step_0_process_correct'] for k in dict2)

    for d1_key, desc in d1_check_keys.items():
        data_list = dict1.get(d1_key, [])
        is_list_true = False
        if not data_list:
            if search_ran_significantly: 
                is_list_true = False
                d1_explanations.append(f"Dict1['{d1_key}'] is empty despite search activity; assumed False for this termination check component.")
            else: 
                is_list_true = True
                d1_explanations.append(f"Dict1['{d1_key}'] is empty, and minimal/no search activity in Dict2 that would require these checks; assumed True.")
        else:
            is_list_true = all(data_list)
            d1_explanations.append(f"{desc} is {is_list_true} (list length: {len(data_list)}).")
        if not is_list_true:
            all_d1_correct = False

    d2_last_step_correct = dict2.get('step_last_process_correct', False)
    exp_d2_last_step = f"Dict2['step_last_process_correct'] is {d2_last_step_correct}."
    if not isinstance(d2_last_step_correct, bool):
        d2_last_step_correct = False
        exp_d2_last_step = "Dict2['step_last_process_correct'] was missing or not a boolean, defaulted to False."

    all_dict2_term_checks_correct = True
    dict2_term_explanations = []
    dict2_term_checks_found = False
    
    dict2_false_count = 0
    dict2_total_count = 0

    for i in range(1, 1000): # Check step_1_termination_checks, etc.
        step_term_key = f'step_{i}_termination_checks'
        if step_term_key in dict2:
            dict2_term_checks_found = True
            current_flag_val = dict2[step_term_key]
            dict2_total_count += 1
            
            if not isinstance(current_flag_val, bool) or not current_flag_val:
                all_dict2_term_checks_correct = False
                dict2_false_count += 1
            
            dict2_term_explanations.append(f"Dict2['{step_term_key}'] is {current_flag_val}.")
        elif f'step_{i}' not in dict2 and not any(k.startswith(f'step_{i}_') for k in dict2):
            break # No more steps

    # Count step_last_process_correct in totals if it exists
    if 'step_last_process_correct' in dict2:
        dict2_total_count += 1
        if not d2_last_step_correct:
            dict2_false_count += 1

    exp_dict2_term_checks = "No step_X_termination_checks keys found in Dict2; this part of check is skipped or assumed covered by step_last_process_correct."
    # If no actual algorithm steps ran, these checks might not be present or relevant.
    if not search_ran_significantly and not dict2_term_checks_found:
        all_dict2_term_checks_correct = True # Vacuously true
        exp_dict2_term_checks = "No significant algorithm steps ran and no step_X_termination_checks found; this part of check is vacuously true."
    elif dict2_term_checks_found:
        exp_dict2_term_checks = f"All Dict2 step_X_termination_checks flags are True: {all_dict2_term_checks_correct}. Details: {' '.join(dict2_term_explanations)}"
    elif search_ran_significantly and not dict2_term_checks_found: 
         exp_dict2_term_checks = "Search ran, but no step_X_termination_checks keys found in Dict2; this part of check is passed if other termination logic is sound."

    final_value = all_d1_correct and d2_last_step_correct and all_dict2_term_checks_correct
    final_explanation = (f"Search Stop Condition Correctness: {' '.join(d1_explanations)} {exp_d2_last_step} {exp_dict2_term_checks}")
    
    # return final_value, final_explanation, dict2_false_count, dict2_total_count
    return (dict2_false_count, dict2_total_count), final_explanation

def get_search_completeness(dict1, dict2):
    """Infers search completeness from Dict2."""
    value = dict2.get('step_last_process_correct', False)
    explanation = (f"Based on Dict2['step_last_process_correct'], which is {value}. "
                   "This infers that the search's known final step completed correctly, suggesting no premature end due to internal algorithm exceptions.")
    if not isinstance(value, bool):
        value = False
        explanation = "Dict2['step_last_process_correct'] was missing or not a boolean, defaulted to False for search completeness."
    if value == True:
        op = (0, 1)
    else:
        op = (1, 1)
    return op, explanation

def get_solve_rate(dict1, dict2):
    """Determines if the search reached the goal (solved the problem)."""
    reached_goal_list = dict1.get('reached_goal', [])
    value = False
    explanation = ""

    if reached_goal_list:
        # The last entry in 'reached_goal' list should reflect the final outcome.
        final_status = reached_goal_list[-1]
        if isinstance(final_status, bool):
            value = final_status
            explanation = f"Value from the last element of Dict1['reached_goal']: {value}. (List: {reached_goal_list})"
        else:
            value = False 
            explanation = f"Last element of Dict1['reached_goal'] is not a boolean ({final_status}). Defaulted to False. (List: {reached_goal_list})"
    else:
        # If list is empty, implies goal status not determined or search failed early.
        search_completed_meaningfully = dict2.get('step_last_process_correct', False)
        if search_completed_meaningfully:
            explanation = "Dict1['reached_goal'] is empty, but search indicates completion (step_last_process_correct is True). This implies goal was not reached. Solve rate is False."
        else:
            explanation = "Dict1['reached_goal'] is empty, and search may not have completed meaningfully (step_last_process_correct is False or missing). Solve rate is False."
        value = False
    if value == True:
        op = (0,1)
    else:
        op = (1,1)
    return op, explanation

def generate_preferred_dict(dict1, dict2):
    """
    Generates the preferred dictionary with attributes derived from dict1 and dict2,
    and a corresponding dictionary of explanations.
    """
    preferred_dict = {}
    explanations_dict = {}

    # Attribute 1: Search Start
    val, exp = get_search_start_correct(dict1, dict2)
    preferred_dict['Search Start'] = val
    explanations_dict['Search Start'] = exp

    # Attribute 2: Heap Pop
    val, exp = get_heap_pop_correct(dict1, dict2)
    preferred_dict['Heap Pop'] = val
    explanations_dict['Heap Pop'] = exp

    # Attribute 3: Add to Visited (Closed) Set
    val, exp = get_add_to_visited_correct(dict1, dict2)
    preferred_dict['Add to Visited (Closed) Set'] = val
    explanations_dict['Add to Visited (Closed) Set'] = exp

    # Attribute 4: Correct Neighbors
    val, exp = get_correct_neighbors(dict1, dict2)
    preferred_dict['Correct Neighbors'] = val
    explanations_dict['Correct Neighbors'] = exp

    # Attribute 5: Neighbor Exploration
    val, exp = get_neighbor_exploration_correct(dict1, dict2)
    preferred_dict['Neighbor Exploration'] = val
    explanations_dict['Neighbor Exploration'] = exp

    # Attribute 6: Newly Discovered Cost
    val, exp = get_newly_discovered_cost_correct(dict1, dict2)
    preferred_dict['Newly Discovered Cost'] = val
    explanations_dict['Newly Discovered Cost'] = exp

    # Attribute 7: Cost Inequality Check
    val, exp = get_cost_inequality_check_correct(dict1, dict2)
    preferred_dict['Cost Inequality Check'] = val
    explanations_dict['Cost Inequality Check'] = exp

    # Attribute 8: Costs Dictionary Update
    val, exp = get_costs_dictionary_update_correct(dict1, dict2)
    preferred_dict['Costs Dictionary Update'] = val
    explanations_dict['Costs Dictionary Update'] = exp

    # Attribute 9: Estimated Value (Total Cost) Calculation
    val, exp = get_estimated_value_calculation_correct(dict1, dict2)
    preferred_dict['Estimated Value (Total Cost) Calculation'] = val
    explanations_dict['Estimated Value (Total Cost) Calculation'] = exp

    # Attribute 10: Heap Push
    val, exp = get_heap_push_correct(dict1, dict2)
    preferred_dict['Heap Push'] = val
    explanations_dict['Heap Push'] = exp

    # Attribute 11: Path Update
    val, exp = get_path_update_correct(dict1, dict2)
    preferred_dict['Path Update'] = val
    explanations_dict['Path Update'] = exp

    # Attribute 12: Search Stop Condition
    val, exp = get_search_stop_correct(dict1, dict2)
    preferred_dict['Search Stop Condition'] = val
    explanations_dict['Search Stop Condition'] = exp

    # Attribute 13: Search Completeness
    val, exp = get_search_completeness(dict1, dict2)
    preferred_dict['Search Completeness'] = val
    explanations_dict['Search Completeness'] = exp
    
    # Attribute 14: Valid Search Trace
    relevant_attributes = [
        'Search Start', 'Heap Pop', 'Add to Visited (Closed) Set', 
        'Correct Neighbors', 'Neighbor Exploration', 'Newly Discovered Cost',
        'Cost Inequality Check', 'Costs Dictionary Update', 
        'Estimated Value (Total Cost) Calculation', 'Heap Push', 'Path Update',
        'Search Stop Condition', 'Search Completeness'
    ]
    
    all_first_elements_zero = all(preferred_dict[attr][0] == 0 for attr in relevant_attributes)
    
    if all_first_elements_zero:
        preferred_dict['Valid Search Trace'] = (0, 1)
        explanations_dict['Valid Search Trace'] = "All first elements of tuples from 'Search Start' through 'Search Completeness' are 0."
    else:
        preferred_dict['Valid Search Trace'] = (1, 1)
        non_zero_attributes = [attr for attr in relevant_attributes if preferred_dict[attr][0] != 0]
        explanations_dict['Valid Search Trace'] = (f"Not all first elements are 0. "
                                                 f"Non-zero first element attributes: {', '.join(non_zero_attributes)}.")

    val, exp = get_solve_rate(dict1, dict2)
    preferred_dict['Solve Rate'] = val
    explanations_dict['Solve Rate'] = exp
    
    return preferred_dict, explanations_dict
#################
# Evolution Start
#################

# json_folder = "/content/drive/MyDrive/books/searchformer-maze/gpt-4o-mini-traces/traces/"
json_folder = "/content/drive/MyDrive/books/searchformer-maze/gpt-4o-traces/traces"
traces = [f for f in os.listdir(json_folder) if f.endswith(".json")]
trace_paths = [os.path.join(json_folder, trace) for trace in traces]

full_df = pd.DataFrame()
for t in trace_paths:
    with open(t) as f:
        data = json.load(f)

    b = "\n".join([m['content'] for m in data["messages"]])
    a = b.split("[81, 82, 83, 73, 74, 75, 65, 66, 67]")[2]# This is the final line of the icl trace

    dict1 = consistency_calculations_checks_wrt_GT(a)
    dict2 = check_process(a)

    df = pd.DataFrame(generate_preferred_dict(dict1, dict2)[0])
    df['File Name'] = os.path.basename(t)

    df['Type'] = list(itertools.islice(itertools.cycle(['Error Count', 'Total Checks']), len(df)))

    full_df = pd.concat([full_df, df], ignore_index=True)

full_df = full_df[['File Name', 'Type', 'Search Start', 'Heap Pop', 'Add to Visited (Closed) Set',
       'Correct Neighbors', 'Neighbor Exploration', 'Newly Discovered Cost',
       'Cost Inequality Check', 'Costs Dictionary Update',
       'Estimated Value (Total Cost) Calculation', 'Heap Push', 'Path Update',
       'Search Stop Condition', 'Search Completeness', 'Valid Search Trace',
       'Solve Rate']]

full_df.drop(columns = ["Search Completeness"], inplace = True)
full_df.rename(columns = {"Solve Rate": "Search Completeness"}, inplace = True)

# full_df.to_csv("result_gpt_4o.csv")
full_df