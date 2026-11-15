# PERKINS | COMPACT-X | Process Simulation

## Buffer

| name | init | capacity |
|:---|:---|:---|
| buffer #1 | 0 | 2 |
| buffer #2 | 0 | 6 |
| buffer #3 | 0 | 2 |

## Machine

### OP0100/0300

#### Connections

| inlet | outlet |
|:---|:---|
| - | buffer #1 |

#### Parameters

| name | parameter | type | distribution | mean | std | value | unit | probability | every |
|:---|:---|:---|:---|:---|:---|:---|:---|:---|:---|
| - | cycle_time | - | normal | 18.0 | 0.10 | - | minutes | - | - |
| maintenance | trigger | operating_time | exponential | 90.0 | - | - | hours | - | - |
| maintenance | time_to_repair | operating_time | lognormal | 1.75 | 1.0 | - | hours | - | - |
| tool_change | trigger | cycle_count | - | - | - | - | - | - | 250 |
| tool_change | time_to_repair | - | fixed | - | - | 5.0 | minutes | - | - |

### OP0400

#### Connections

| inlet | outlet |
|:---|:---|
| buffer #1 | buffer #2 |

#### Parameters

| name | parameter | type | distribution | mean | std | value | unit | probability | every |
|:---|:---|:---|:---|:---|:---|:---|:---|:---|:---|
| - | cycle_time | - | normal | 22.0 | 0.10 | - | minutes | - | - |
| maintenance | trigger | operating_time | exponential | 75.0 | - | - | hours | - | - |
| maintenance | time_to_repair | operating_time | lognormal | 1.75 | 1.0 | - | hours | - | - |
| tool_change | trigger | cycle_count | - | - | - | - | - | - | 175 |
| tool_change | time_to_repair | - | fixed | - | - | 5.0 | minutes | - | - |
| special_tool_change | trigger | cycle_count | - | - | - | - | - | - | 120 |
| special_tool_change | time_to_repair | - | fixed | - | - | 4.0 | hours | - | - |

### OP0500

#### Connections

| inlet | outlet |
|:---|:---|
| buffer #2 | buffer #3 |

#### Parameters

| name | parameter | type | distribution | mean | std | value | unit | probability | every |
|:---|:---|:---|:---|:---|:---|:---|:---|:---|:---|
| - | cycle_time | - | normal | 18.0 | 0.25 | - | minutes | - | - |

### OP0600

#### Connections

| inlet | outlet |
|:---|:---|
| buffer #3 | - |

#### Parameters

| name | parameter | type | distribution | mean | std | value | unit | probability | every |
|:---|:---|:---|:---|:---|:---|:---|:---|:---|:---|
| - | cycle_time | - | normal | 18.0 | 0.25 | - | minutes | - | - |

## Output

| parameter | value |
| --- | --- |
| output_dir | results |
| csv | true |
| plots | true |
