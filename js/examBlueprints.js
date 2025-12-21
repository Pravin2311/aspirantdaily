export const EXAM_BLUEPRINTS = {
  ssc: {
    refresh: "daily",
    sections: [
      { subject: "reasoning", count: 6 },
      { subject: "quant", count: 6 },
      { subject: "english", count: 5 },
      { subject: "science", count: 4 },
      { subject: "current-affairs", count: 4 }
    ]
  },

  bank: {
    refresh: "daily",
    sections: [
      { subject: "reasoning", count: 8 },
      { subject: "quant", count: 8 },
      { subject: "english", count: 6 },
      { subject: "computer", count: 3 }
    ]
  },

  rrb: {
    refresh: "weekly",
    sections: [
      { subject: "reasoning", count: 6 },
      { subject: "science", count: 6 },
      { subject: "static-gk", count: 5 },
      { subject: "current-affairs", count: 4 },
      { subject: "english", count: 4 }
    ]
  },

  psc: {
    refresh: "weekly",
    sections: [
      { subject: "static-gk", count: 6 },
      { subject: "science", count: 5 },
      { subject: "economics", count: 5 },
      { subject: "geography", count: 5 },
      { subject: "current-affairs", count: 4 }
    ]
  },

  cuet: {
    refresh: "daily",
    sections: [
      { subject: "english", count: 6 },
      { subject: "reasoning", count: 5 },
      { subject: "science", count: 5 },
      { subject: "static-gk", count: 4 },
      { subject: "current-affairs", count: 5 }
    ]
  },

  upsc: {
    refresh: "daily",
    sections: [
      { subject: "current-affairs", count: 8 },
      { subject: "economics", count: 6 },
      { subject: "geography", count: 5 },
      { subject: "static-gk", count: 4 },
      { subject: "science", count: 2 }
    ]
  },

  mixed: {
    refresh: "daily",
    sections: [
      { subject: "reasoning", count: 4 },
      { subject: "quant", count: 4 },
      { subject: "english", count: 4 },
      { subject: "science", count: 4 },
      { subject: "economics", count: 3 },
      { subject: "geography", count: 3 },
      { subject: "current-affairs", count: 3 }
    ]
  }
};
