export interface Lesson {
  lesson_id: string;
  title: string;
  level: string;
  module: string;
  analytical_question: string;
  default_dataset_id: string;
  default_country: string;
  target_variable?: string | null;
  candidate_variables: string[];
  learning_objectives: string[];
  concepts: { name: string; plain_english: string }[];
  review_questions: string[];
  required_outputs: string[];
}

