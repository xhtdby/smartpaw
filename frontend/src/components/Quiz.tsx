"use client";

import { useState } from "react";
import quizData from "../../../backend/data/learn_quizzes.json";

type PageLanguage = "en" | "hi" | "mr";

type QuizQuestion = {
  source_entry_id: string;
  q: Record<PageLanguage, string>;
  options: Record<PageLanguage, string[]>;
  correct_index: number;
  explanation: Record<PageLanguage, string>;
};

const QUIZZES = quizData as Record<string, QuizQuestion[]>;

const TOPIC_ALIASES: Record<string, string> = {
  heatstroke: "heat",
  poisoning: "poison",
  "road-trauma": "trauma",
  "skin-ticks": "skin",
};

const COPY: Record<
  PageLanguage,
  { title: string; correct: string; incorrect: string }
> = {
  en: {
    title: "Quick check",
    correct: "Correct",
    incorrect: "Not quite",
  },
  hi: {
    title: "त्वरित जांच",
    correct: "सही",
    incorrect: "पूरी तरह नहीं",
  },
  mr: {
    title: "झटपट तपासणी",
    correct: "बरोबर",
    incorrect: "पूर्णपणे नाही",
  },
};

export function Quiz({
  topicId,
  language,
}: {
  topicId: string;
  language: PageLanguage;
}) {
  const questions = QUIZZES[topicId] ?? QUIZZES[TOPIC_ALIASES[topicId]] ?? [];
  const [answers, setAnswers] = useState<Record<number, number>>({});
  const copy = COPY[language] ?? COPY.en;

  if (questions.length === 0) return null;

  return (
    <div className="mt-4 border-t border-gray-100 pt-4">
      <h4 className="text-sm font-semibold text-[var(--color-warm-700)] mb-3">
        {copy.title}
      </h4>
      <div className="space-y-4">
        {questions.map((question, questionIndex) => {
          const selected = answers[questionIndex];
          const answered = selected !== undefined;
          const isCorrect = selected === question.correct_index;

          return (
            <div key={`${topicId}-${questionIndex}`} className="space-y-2">
              <p className="text-sm font-medium text-gray-800">{question.q[language]}</p>
              <div className="grid gap-2">
                {question.options[language].map((option, optionIndex) => {
                  const isSelected = selected === optionIndex;
                  const isAnswer = question.correct_index === optionIndex;
                  const stateClass =
                    answered && isAnswer
                      ? "border-emerald-300 bg-emerald-50 text-emerald-800"
                      : answered && isSelected
                        ? "border-red-300 bg-red-50 text-red-800"
                        : "border-gray-200 bg-white text-gray-700";

                  return (
                    <button
                      key={`${optionIndex}-${option}`}
                      type="button"
                      onClick={() =>
                        setAnswers((current) => ({ ...current, [questionIndex]: optionIndex }))
                      }
                      aria-pressed={isSelected}
                      className={`w-full rounded-lg border px-3 py-2 text-left text-sm leading-relaxed transition-colors ${stateClass}`}
                    >
                      {option}
                    </button>
                  );
                })}
              </div>
              {answered && (
                <div
                  className={`rounded-lg px-3 py-2 text-sm leading-relaxed ${
                    isCorrect
                      ? "bg-emerald-50 text-emerald-800"
                      : "bg-amber-50 text-amber-900"
                  }`}
                >
                  <span className="font-semibold">
                    {isCorrect ? copy.correct : copy.incorrect}:{" "}
                  </span>
                  {question.explanation[language]}
                </div>
              )}
            </div>
          );
        })}
      </div>
    </div>
  );
}
