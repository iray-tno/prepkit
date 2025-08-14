# GitHub Copilot Configuration for PrepKit

## Copilot Settings (.vscode/settings.json)

```json
{
  "github.copilot.enable": {
    "*": true,
    "cpp": true,
    "python": true,
    "yaml": true
  },
  "github.copilot.inlineSuggest.enable": true,
  "github.copilot.advanced": {
    "indentationMode": {
      "cpp": "space", 
      "python": "space"
    }
  }
}
```

## Code Snippets for IntelliSense

### C++ Competitive Programming Templates

```cpp
// prepkit_main - Main template with fast IO
#include <iostream>
#include <vector>
#include <algorithm>
using namespace std;

constexpr int MOD = 1000000007;

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);
    
    // Solution here
    
    return 0;
}

// prepkit_segtree - Segment tree template
class SegmentTree {
private:
    vector<long long> tree;
    int size;
    
    void update_impl(int node, int start, int end, int idx, int val) {
        if (start == end) {
            tree[node] = val;
        } else {
            int mid = (start + end) / 2;
            if (idx <= mid) {
                update_impl(2 * node, start, mid, idx, val);
            } else {
                update_impl(2 * node + 1, mid + 1, end, idx, val);
            }
            tree[node] = tree[2 * node] + tree[2 * node + 1];
        }
    }
    
public:
    SegmentTree(int n) : size(n) { tree.resize(4 * n); }
    void update(int idx, int val) { update_impl(1, 0, size - 1, idx, val); }
    long long query(int l, int r) { return query_impl(1, 0, size - 1, l, r); }
};

// prepkit_debug - Debug utilities  
#ifdef LOCAL_DEBUG
#define dbg(x) cerr << #x << " = " << (x) << endl
#define dbg_arr(arr, n) cerr << #arr << ": "; for(int i = 0; i < (n); i++) cerr << arr[i] << " "; cerr << endl
#else
#define dbg(x)
#define dbg_arr(arr, n)  
#endif
```

### Python Experiment Templates

```python
# prepkit_experiment - WandB experiment setup
import wandb
import hydra
from omegaconf import DictConfig

@hydra.main(config_path="conf", config_name="config", version_base=None)
def main(cfg: DictConfig) -> None:
    wandb.init(project=cfg.wandb.project, entity=cfg.wandb.entity)
    
    # Experiment code here
    
    wandb.finish()

# prepkit_kaggle_submit - Kaggle submission with WandB
def submit_with_logging(submission_file: str, competition: str, message: str):
    import subprocess
    result = subprocess.run([
        'prepkit', 'kaggle', 'submit-competition', 
        submission_file, '--competition', competition, 
        '--message', message, '--log-wandb'
    ])
    return result.returncode == 0
```

## Auto-completion Triggers

Configure Copilot to trigger on these comment patterns:

```cpp
// TODO: Implement segment tree for range queries
// OPTIMIZE: Use constexpr for better performance
// PREPROCESS: This will be minified for Codingame
// TEMPLATE: Generate AtCoder boilerplate
```

## Copilot Chat Commands

Use these commands in Copilot Chat:

```
/explain this competitive programming algorithm
/optimize this code for memory usage
/tests generate test cases for edge conditions  
/fix resolve compilation errors for single-file output
```

## Language-Specific Optimizations

### C++ Competitive Programming
- Prefer `vector` over dynamic arrays
- Use `constexpr` for compile-time constants
- Optimize I/O with `ios::sync_with_stdio(false)`
- Template meta-programming for repeated patterns

### Python Experiment Management
- Type hints for better Copilot suggestions
- Hydra configuration patterns
- WandB logging conventions
- Error handling for subprocess calls

## Workspace Configuration

Create `.copilot-workspace.yml`:
```yaml
contexts:
  competitive-programming:
    patterns: ["*.cpp", "tests/*.cpp"]
    description: "C++ competitive programming solutions"
    
  experiment-management: 
    patterns: ["src/experiment_manager.py", "configs/**/*.yaml"]
    description: "ML experiment configuration and management"
    
  preprocessing:
    patterns: ["src/plugins/cpp_plugin.py", "tests/test_cpp_*.py"] 
    description: "C++ preprocessing and minification"
```