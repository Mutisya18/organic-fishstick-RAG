The 10 NASA coding rules
1. Avoid complex control flow.
Do not use goto, setjmp, or longjmp, avoid writing recursive functions in any part of the code.

‍❌ Non Compliant example

// Non-compliant: recursive function call
int factorial(int n) {
    if (n <= 1) return 1;
    return n * factorial(n-1);   // recursion (direct)
}
✅ Compliant example (uses loop)

// Compliant: uses an explicit loop instead of recursion
int factorial(int n) {
    int result = 1;
    for (int i = n; i > 1; --i) {
        result *= i;
    }
    return result;
}
Why this matters: Recursion and gotos create non-linear control flow that is hard to reason about.  Recursive calls make the call graph cyclic and stack depth unbounded; goto creates spaghetti code. By using simple loops and straight-line code, a static analyzer can easily verify stack usage and program paths. Violating this rule could lead to unexpected stack overflows or logic paths that are hard to review manually.

2. Loops must have fixed upper bounds.
Every loop should have a compile-time verifiable limit.

❌ Non Compliant example (unbounded loop):

// Non-compliant: loop with dynamic or unknown bound
int i = 0;
while (array[i] != 0) {
    doSomething(array[i]);
    i++;
}
✅ Compliant example (fixed-bound loop):

// Compliant: loop with explicit fixed upper bound and assert
#define MAX_LEN 100
for (int i = 0; i < MAX_LEN; i++) {
    if (array[i] == 0) break;
    doSomething(array[i]);
}
Why this matters: Unbounded loops can run forever or exceed resource limits.  With a fixed bound, tools can statically prove the maximum iterations. In safety-critical systems, a missing bound could cause a runaway loop. By enforcing an explicit limit (or a static array size), we ensure loops terminate predictably .  Without this rule, an error in loop logic might not be caught until deployment (e.g. an off-by-one that causes an infinite loop).

3. No dynamic memory after initialization.
Avoid malloc/free or any heap use in running code; only use fixed or stack allocation.

❌ Non Compliant example (uses malloc)

// Non-compliant: dynamic allocation inside the code
void storeData(int size) {
    int *buffer = malloc(size * sizeof(int));
    if (buffer == NULL) return;
    // ... use buffer ...
    free(buffer);
}
✅ Compliant example (static allocation)

// Compliant: fixed-size array on stack or global
#define MAX_SIZE 256
void storeData() {
    int buffer[MAX_SIZE];
    // ... use buffer without dynamic alloc ...
}
Why this matters: Dynamic memory allocation during runtime can lead to unpredictable behavior, memory fragmentation, or allocation failures, especially in systems with limited resources like spacecraft or embedded controllers. If malloc or free fails mid-mission, the software might crash or behave unpredictably. Using only fixed-size or stack-allocated memory ensures deterministic behavior, simplifies validation, and prevents runtime memory leaks.

4. Functions fit on one page (~60 lines).
Keep each function short (roughly ≤ 60 lines).

❌ Non Compliant example

// Non-compliant: hundreds of lines in one function (not shown)
void processAllData() {
    // ... imagine 100+ lines of code doing many tasks ...
}
✅ Compliant example (modular functions)

// Compliant: break the task into clear sub-functions
void processAllData() {
    preprocessData();
    analyzeData();
    postprocessData();
}
void preprocessData() { /* ... */ }
void analyzeData()   { /* ... */ }
void postprocessData(){ /* ... */ }
Why this matters: Extremely long functions are hard to understand, test, and verify as a unit .  By keeping each function limited to one conceptual task (and within a printed page), code reviews and static checks become tractable.  If a function spans too many lines, logical errors or boundary conditions can be missed. Breaking code into smaller functions improves clarity and makes it easier to enforce other rules (like assertion density and return checks per function).

5. Use at least two assert statements per function.
Each function should perform defensive checks.

❌ Non Compliant example (no assecrtions):

int get_element(int *array, size_t size, size_t index) {
return array[index];
}
✅ Compliant example (with assertions):

int get_element(int *array, size_t size, size_t index) {
    assert(array != NULL);        // Assertion 1: pointer validity
    assert(index < size);          // Assertion 2: bounds check
    
    if (array == NULL) return -1;  // Recovery: return error
    if (index >= size) return -1;  // Recovery: return error
    
    return array[index];
}
Why this matters: Assertions are the first line of defense against invalid conditions.  NASA found that a higher assertion density significantly increases the chance to catch bugs .  With at least two asserts per function (checking preconditions, limits, invariants), the code self-documents its assumptions and immediately flags anomalies during testing.  Without asserts, an unexpected value might silently propagate, causing failure far from the source of the error.

6. Declare data with minimal scope.
Keep variables as local as possible; avoid globals.

❌ Non Compliant example (gloabl data):

// Non-compliant: global variable visible everywhere
int statusFlag;
void setStatus(int f) {
    statusFlag = f;
}
✅ Compliant example (local scope):

// Compliant: local variable inside function
void setStatus(int f) {
    int statusFlag = f;
    // ... use statusFlag only here ...
}
Why this matters: Minimizing scope reduces coupling and unintended interactions.  If a variable is only needed within a function, declaring it globally risks other code altering it unexpectedly .  By keeping data local, each function becomes more self-contained and side-effect free, which simplifies analysis and testing.  Violations (like reusing global state) can lead to hard-to-find bugs due to aliasing or unexpected modifications.

7. Check all function return values and parameters.
The caller must examine every non-void return value; every function must validate its input parameters.

❌ Non Compliant example (ignores return value)

int bad_mission_control(int velocity, int time) {
    int distance;
    calculate_trajectory(velocity, time, &distance);  // Didn't check!
    return distance;  // Could be garbage if calculation failed
}
✅ Compliant example

int good_mission_control(int velocity, int time) {
    int distance;
    int status = calculate_trajectory(velocity, time, &distance);
    
    if (status != 0) {  // Checked the return value
        return -1;  // Propagate error to caller
    }
    
    return distance;  // Safe to use
}
Why this matters: Ignoring return values or invalid parameters is a major source of bugs . For example, failing to check malloc might lead to a null-pointer dereference. Likewise, not validating inputs (e.g. array indices or format strings) can cause buffer overflows or crashes. NASA requires every return to be handled (or explicitly cast to void to signal intent), and every argument to be verified. This catch-all approach ensures no error is silently ignored.

8. Limit the preprocessor to includes and simple macros.
Avoid complex macros or conditional compilation tricks.

❌ Non Compliant example (complex marco):

#define DECLARE_FUNC(name) void func_##name(void)

DECLARE_FUNC(init);  // Expands to: void func_init(void)
✅ Compliant example (simple macros / inline):

// Compliant: use inline function or straightforward definitions
static inline int sqr(int x) { return x*x; }
#define MAX_BUFFER 256
Why this matters: Complex macros (especially multi-line or function-like macros) can hide logic, confuse control flow, and thwart static analysis.  Limiting the preprocessor to trivial tasks (e.g. constants and headers) keeps the code explicit.  For example, replacing macros with inline functions improves type checking and debuggability.  Without this rule, subtle macro expansion bugs or conditional-compilation errors might slip through reviews unnoticed.

9. Limit pointer usage.
Limit indirection to a single level—avoid int** and function pointers.

❌ Non Compliant example (multiple inderection):

// Non-compliant: double pointer and function pointer
int **doublePtr;
int (*funcPtr)(int) = someFunction;
✅ Compliant example (single pointer):

// Compliant: single-level pointer, no function pointers
int *singlePtr;
// Use explicit call instead of function pointer
int result = someFunction(5);
Why this matters: Multiple levels of pointers and function pointers complicate data flow and make it hard to follow what memory or code is being accessed.  Static analyzers must resolve each indirection, which can be undecidable in general. By restricting to single-pointer references, the code stays simpler and safer.  Violating this can lead to unclear aliasing (one pointer modifying data through another) or unexpected callback behavior, both of which are risky in safety-critical contexts.

10. Compile with all warnings enabled and fix them.
Enable every compiler warning and address them before release.

❌ Non Compliant example (code with warnings)

// Non-compliant: code that generates warnings (uninitialized, suspicious assignment)
int x;
if (x = 5) {  // bug: should be '==' or initialize x
    // ...
}
printf("%d\n", x);  // warning: 'x' is used uninitialized
✅ Compliant example (clean compile)

// Compliant: initialize variables and use '==' in condition
int x = 0;
if (x == 5) {
    // ...
}
printf("%d\n", x);
Why this matters: Compiler warnings often flag genuine bugs (like uninitialized variables, type mismatches, or unintended assignments).  NASA’s rule mandates that no warning is ignored. Before any release, the code should compile without warnings under maximum-verbosity settings. This practice catches many trivial mistakes early. If a warning cannot be resolved, the code should be restructured or documented so that the warning never occurs in the first place.
