int main() {
    int a = 10;
    int b = 2;
    int res = 0;

    if (a > 5) {
        res = a * b + 4;
    } else {
        res = 0;
    }

    printf(res);

    int counter = 3;
    while (counter > 0) {
        printf(counter);
        counter = counter - 1;
    }

    return 0;
}
