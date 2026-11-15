# Esempio: fermi configurabili

## Buffer

| name | init | capacity |
| --- | --- | --- |

## Machine

### CU-115

#### Connections

| inlet | outlet |
| --- | --- |
| - | - |

#### Parameters

| name | parameter | type | distribution | mean | std | value | unit | probability | every | blocks_machine |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| - | cycle_time | - | normal | 5.78 | 0.54 | - | minutes | - | - | - |
| maintenance | trigger | operating_time | normal | 90.0 | 3.0 | - | hours | - | - | true |
| maintenance | time_to_repair | - | normal | 10.0 | 1.0 | - | minutes | - | - | - |
| quality | trigger | per_cycle | - | - | - | - | - | 0.008 | - | false |
| quality | time_to_repair | - | normal | 15.0 | 3.0 | - | minutes | - | - | - |
| tool_change | trigger | cycle_count | - | - | - | - | - | - | 500 | false |
| tool_change | time_to_repair | - | fixed | - | - | 5.0 | minutes | - | - | - |
| special_tool_change | trigger | cycle_count | - | - | - | - | - | - | 2000 | false |
| special_tool_change | time_to_repair | - | normal | 15.0 | 2.0 | - | minutes | - | - | - |

## Output

| parameter | value |
| --- | --- |
| output_dir | results |
| csv | true |
| plots | true |
