def calculate_exam_results(scores, pass_grade=60):
    total = sum(scores)
    count = len(scores)
    avg_score = total / count
    max_score = max(scores)
    min_score = min(scores)

    passed_count = 0
    above_avg_count = 0

    for score in scores:
        if score >= pass_grade:
            passed_count += 1
        if score > avg_score:
            above_avg_count += 1

    pass_percentage = (passed_count / count) * 100

    return avg_score, max_score, min_score, passed_count, pass_percentage, above_avg_count


def show_menu():
    print("\n===== МЕНЮ (Результаты экзамена) =====")
    print("1. Ввести баллы и показать аналитику")
    print("0. Выход")


def main():
    while True:
        show_menu()
        choice = input("Выберите действие: ")

        if choice == "1":
            count = int(input("Введите количество студентов: "))
            if count <= 0:
                print("Ошибка: количество студентов должно быть больше 0!")
                continue

            scores = []
            for i in range(count):
                score = float(input(f"Введите баллы студента №{i + 1} (от 0 до 100): "))
                if score < 0 or score > 100:
                    print("Некорректный балл, будет записан как 0.")
                    score = 0.0
                scores.append(score)

            avg, max_s, min_s, passed, pass_pct, above_avg = calculate_exam_results(scores)

            print("\n--- Итоги экзамена ---")
            print(f"Средний балл: {avg}")
            print(f"Максимальный балл: {max_s}")
            print(f"Минимальный балл: {min_s}")
            print(f"Количество сдавших: {passed}")
            print(f"Процент сдавших: {pass_pct}%")
            print(f"Студентов с результатом выше среднего: {above_avg}")

        elif choice == "0":
            print("Выход из программы.")
            break
        else:
            print("Неверный пункт меню, попробуйте снова.")


if __name__ == "__main__":
    main()