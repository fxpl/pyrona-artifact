from bocpy import send, receive
from matrix import Matrix

try:
    import _interpreters as interpreters
except ModuleNotFoundError:
    import _xxsubinterpreters as interpreters

try:
    ip_id = interpreters.get_current()[0]
    running = True
    matrix_inverse = Matrix()

    send("started", True)
    while running:
        match receive("worker"):
            case ["worker", "shutdown"]:
                running = False

            case ["worker", cown]:
                cown.acquire()
                values = cown.value.values
                count = 0
                for matrix in values:
                    if matrix.invert(matrix_inverse):
                        count += 1

                del matrix
                del values

                cown.release()
                send("result", count)
except Exception as ex:
    print(ex)
