# demo.py - intentionally inefficient code to trigger Carbon Optimizer diagnostics

import time

# 1. Nested loops (HIGH severity) - O(n^3) complexity
def find_triplets(data):
    results = []
    for i in range(len(data)):
        for j in range(len(data)):
            for k in range(len(data)):
                if data[i] + data[j] + data[k] == 0:
                    results.append((data[i], data[j], data[k]))
    return results

# 2. Repeated sub-expression inside loop (MEDIUM severity)
def compute_distances(points):
    distances = []
    for i in range(len(points)):
        # len(points) is re-evaluated every iteration
        for j in range(len(points)):
            dx = points[i][0] - points[j][0]
            dy = points[i][1] - points[j][1]
            dist = (dx ** 2 + dy ** 2) ** 0.5
            distances.append(dist)
    return distances

# 3. Inefficient string concatenation in a loop (MEDIUM severity)
def build_report(items):
    report = ""
    for item in items:
        report = report + str(item) + ", "
    return report

# 4. Repeated list membership check instead of set (MEDIUM severity)
def find_duplicates(data):
    seen = []
    duplicates = []
    for item in data:
        if item in seen:          # O(n) lookup on a list
            duplicates.append(item)
        else:
            seen.append(item)
    return duplicates

# 5. Deeply nested conditionals inside a loop (HIGH severity)
def process_records(records):
    output = []
    for record in records:
        for field in record:
            for value in record[field]:
                if value > 0:
                    if value < 100:
                        if value % 2 == 0:
                            output.append(value * 2)
    return output


if __name__ == "__main__":
    data = list(range(-5, 6))
    print(find_triplets(data))

    points = [(i, i * 2) for i in range(10)]
    print(compute_distances(points))

    print(build_report(range(20)))
    print(find_duplicates([1, 2, 3, 2, 4, 1, 5]))
    print(process_records([{"a": [1, 2, 3], "b": [50, 150]}]))
