from bocpy import send, receive
from matrix import Matrix

try:
    running = True
    matrix_inverse = Matrix()

    send("started", True)
    while running:
        match receive("worker"):
            case ["worker", "shutdown"]:
                running = False

            case ["worker", values]:
                count = 0
                for matrix in values:
                    if matrix.invert(matrix_inverse):
                        count += 1

                send("result", count)
except Exception as ex:
    print(ex)
